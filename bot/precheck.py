#!/usr/bin/env python3
"""
precheck.py — turn raw broker JSON into a compact, decision-ready brief.

Runs BEFORE the model reasons. Every mechanical gate is evaluated here so the model
never does arithmetic, never maintains a list, and never has to remember a rule.

    python3 bot/precheck.py            # reads bot/raw/*.json + bot/state.json
    python3 bot/precheck.py --brief bot/brief.md

Design rules:
  1. NEVER crash the cycle. Any failure degrades to a warning in the brief and a
     FAILURE row in the ledger — a broken precheck must not silently disable checks.
  2. Pure read + compute. It does not place orders and does not mutate state.json
     (postcheck.py owns writes), except the failure ledger which is append-only.
"""

from __future__ import annotations
import json, re, sys, os, argparse, datetime as dt, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
RAW = os.path.join(HERE, "raw")
STATE = os.path.join(HERE, "state.json")
LEDGER = os.path.join(HERE, "failures.jsonl")

WARN: list[str] = []
FAIL: list[dict] = []


def warn(msg: str) -> None:
    WARN.append(msg)


def fail(code: str, detail: str, severity: str = "medium", auto_fixable: bool = False) -> None:
    FAIL.append({"code": code, "detail": detail, "severity": severity, "auto_fixable": auto_fixable})


def load(name: str, required: bool = True):
    """Load bot/raw/<name>.json, tolerating the MCP envelope shape."""
    p = os.path.join(RAW, f"{name}.json")
    if not os.path.exists(p):
        if required:
            fail("RAW_MISSING", f"bot/raw/{name}.json not written this cycle", "high", False)
        return None
    try:
        with open(p) as f:
            d = json.load(f)
        return d.get("data", d) if isinstance(d, dict) else d
    except Exception as e:
        fail("RAW_MALFORMED", f"bot/raw/{name}.json: {e}", "high", False)
        return None


def num(x, default=0.0) -> float:
    try:
        if x is None or x == "":
            return default
        return float(x)
    except (TypeError, ValueError):
        return default


def money(x) -> str:
    return f"${x:,.2f}"


def pct(x) -> str:
    return f"{x:+.2f}%"


# ---------------------------------------------------------------- collectors

def collect_quotes(q) -> dict:
    """symbol -> {last, prev}"""
    out = {}
    if not q:
        return out
    for r in (q.get("results") or []):
        quote = r.get("quote") or {}
        sym = quote.get("symbol")
        if not sym:
            continue
        last = num(quote.get("last_trade_price"))
        nonreg = num(quote.get("last_non_reg_trade_price"))
        out[sym] = {
            "last": last or nonreg,
            "prev": num(quote.get("adjusted_previous_close")) or num(quote.get("previous_close")),
        }
    return out


def collect_atr(symbols: list[str]) -> dict:
    """symbol -> ATR value, from bot/raw/atr_<SYM>.json (optional)."""
    out = {}
    for s in symbols:
        p = os.path.join(RAW, f"atr_{s}.json")
        if not os.path.exists(p):
            continue
        try:
            with open(p) as f:
                d = json.load(f)
            d = d.get("data", d)
            series = (d.get("indicators") or [{}])[0].get("series") or []
            if series:
                out[s] = num(series[-1].get("value"))
        except Exception as e:
            warn(f"ATR parse failed for {s}: {e}")
    return out


# ---------------------------------------------------------------- main

def compute_failures(state: dict) -> list[dict]:
    """Re-run the mechanical checks against CURRENT state/raw and return the FAIL list,
    without touching the ledger or brief.md. Used by postcheck.py to auto-resolve any
    precheck-sourced code that no longer reproduces — the alternative is every precheck
    finding staying open forever, since postcheck's own resolve() calls only cover the
    six checks postcheck computes itself.

    Best-effort: if bot/raw/ has been cleared since the fetch step, checks that depend on
    it silently see less data (same degrade-gracefully behaviour as a normal run) rather
    than raising — a stale ledger row is a smaller failure than a crash.
    """
    FAIL.clear()
    WARN.clear()
    try:
        build(state)
    except Exception:
        pass
    return list(FAIL)


def build(state: dict) -> str:
    pol = state.get("policy", {})
    L: list[str] = []
    add = L.append

    portfolio = load("portfolio")
    accounts = load("accounts", required=False)
    positions = load("positions")
    quotes_raw = load("quotes")
    orders = load("orders", required=False)

    quotes = collect_quotes(quotes_raw)

    # ---- cash -------------------------------------------------------------
    total = equity = cash = bp = pending = 0.0
    if portfolio:
        total = num(portfolio.get("total_value"))
        equity = num(portfolio.get("equity_value"))
        cash = num(portfolio.get("cash"))
        pending = num(portfolio.get("pending_deposits"))
        bp = num((portfolio.get("buying_power") or {}).get("buying_power"), cash)

    unsettled = 0.0
    if accounts:
        for a in (accounts.get("accounts") or []):
            if a.get("account_number") == state.get("account_number"):
                unsettled = num(a.get("unsettled_funds"))

    cash_pct = (cash / total * 100.0) if total else 0.0

    add("# PRECHECK BRIEF")
    add(f"_generated {dt.datetime.now(dt.timezone.utc).strftime('%Y-%m-%d %H:%M UTC')} — every number below is computed, not recalled._")
    add("")
    add("## Cash")
    add(f"- **Buying power (authoritative): {money(bp)}** · cash {money(cash)} · unsettled {money(unsettled)}")
    add(f"- Account total {money(total)} · equity {money(equity)} · **cash = {cash_pct:.1f}% of account**")
    if pending:
        add(f"- ⚠ `pending_deposits` reads {money(pending)} — **NON-EVIDENCE, already counted in cash. Do not add to available capital.**")
    if unsettled > 0:
        add(f"- ⚠ {money(unsettled)} unsettled (T+1, cash account) — NOT spendable this cycle.")

    # ---- positions --------------------------------------------------------
    rows = []
    if positions:
        for p in (positions.get("positions") or []):
            sym = p.get("symbol")
            qty = num(p.get("quantity"))
            avg = num(p.get("average_buy_price"))
            if not sym or qty <= 0:
                continue
            last = quotes.get(sym, {}).get("last", 0.0)
            prev = quotes.get(sym, {}).get("prev", 0.0)
            if not last:
                warn(f"no quote for held position {sym} — value/P&L omitted")
            cost = qty * avg
            val = qty * last
            rows.append({
                "sym": sym, "qty": qty, "avg": avg, "last": last, "cost": cost, "val": val,
                "pl": val - cost,
                "pl_pct": ((val / cost - 1.0) * 100.0) if cost else 0.0,
                "day_pct": ((last / prev - 1.0) * 100.0) if prev else 0.0,
            })
    rows.sort(key=lambda r: -r["val"])
    eq = sum(r["val"] for r in rows) or equity
    for r in rows:
        # TWO BASES, DELIBERATELY. They are not interchangeable and the rules disagree:
        #   wt      = % of EQUITY  -> §6 per-name bands (25/30/35 are stated "of equity")
        #   wt_acct = % of TOTAL ACCOUNT -> §C-0/§C-0b tier bands (policy.sizing_basis
        #             == "total_account"; the Sizing section's dollar bands already use it)
        # Before 2026-09-01 only `wt` existed and the brief printed it under a bare "wt%"
        # header, so the §C-0b re-rating comparison — done by the model, by eye, against
        # tier bands defined on the OTHER basis — was reading the wrong column. With cash
        # at 10.2% the two differ by ~11% relative, which straddled the trim threshold on
        # three names, which read as forced trims on the equity basis and as no trim at
        # all on the account basis. Fix: compute both, label both, and decide §C-0b
        # mechanically below.
        r["wt"] = (r["val"] / eq * 100.0) if eq else 0.0
        r["wt_acct"] = (r["val"] / total * 100.0) if total else r["wt"]

    total_cost = sum(r["cost"] for r in rows)
    total_val = sum(r["val"] for r in rows)

    add("")
    add(f"## Positions ({len(rows)}) — cost {money(total_cost)} → value {money(total_val)} = **{pct((total_val/total_cost-1)*100 if total_cost else 0)}**")
    add("")
    add("_**%acct** (of total account) is the §C-0/§C-0b tier basis; **%eq** (of equity) is the "
        "§6 band basis. Compare tiers against %acct — never against %eq._")
    add("")
    add("| sym | tier | %acct | %eq | value | P&L% | day% | §C-0b | review |")
    add("|---|---|---:|---:|---:|---:|---:|---|---|")
    tier_bands = (pol.get("sizing_tiers_pct_account") or
                  {"TIER1": [10, 12], "TIER2": [6, 8], "TIER3": [4, 5]})
    tol = num(pol.get("rerate_tolerance_pts"), 1.5)
    min_new = num(pol.get("min_new_position_pct_account"), 4.0)
    rerate_trim, rerate_add, rerate_declare, rerate_untiered = [], [], [], []
    for r in rows:
        meta = (state.get("positions") or {}).get(r["sym"]) or {}
        # STATE_SAYS_CLOSED — added 2026-09-03. `rows` is built from the BROKER, so every
        # symbol here is genuinely held; a state record still stamped closed/exit_date is
        # state contradicting the live book. Postcheck's re-entry path (fixed the same day)
        # is what let this happen — a name was re-bought into a record closed two days
        # earlier and stayed "closed" while the broker reported the position held. The
        # re-entry fix stops such a record being CREATED;
        # this stops it being READ silently, because everything downstream of state
        # (tier scoring, the §C-0c round-trip guard, §11's per-position benchmark window) trusts
        # these fields. Broker is the fact, state is the claim — say so loudly.
        if meta.get("exit_date") or meta.get("status") == "closed":
            fail("STATE_SAYS_CLOSED",
                 f"{r['sym']} is HELD at the broker but state.json marks it closed "
                 f"(exit {meta.get('exit_date')}) — state contradicts the live book; its "
                 "entry_date/tier/spy_at_entry describe a PRIOR life and must not be scored",
                 "high", False)
        rv = meta.get("review_trigger") or "⚠ NONE SET"
        if rv.startswith("SET ME") or rv == "⚠ NONE SET":
            fail("NO_REVIEW_TRIGGER", f"{r['sym']} has no review trigger (SELF-AUDIT rule 7)", "medium", False)
            rv = "⚠ **MISSING**"
        else:
            rv = (rv[:36] + "…") if len(rv) > 37 else rv

        # ---- §C-0b conviction re-rating, computed on the ACCOUNT basis ----
        lt = meta.get("live_tier")
        w = r["wt_acct"]
        if not lt or lt in ("legacy", "none", "NONE"):
            verdict = "⚠ NO LIVE TIER"
            rerate_untiered.append(r["sym"])
        else:
            lo, hi = tier_bands.get(lt, [0.0, 999.0])
            if w < min_new:
                verdict = f"**SUB-SCALE** <{min_new:g}%"
                rerate_add.append(f"{r['sym']} {w:.1f}% — below the {min_new:g}% minimum: size to a tier or CLOSE")
            elif w > hi + tol:
                verdict = f"**TRIM→{hi:g}%**"
                rerate_trim.append(f"{r['sym']} {w:.1f}% is >{tol:g}pts above {lt} top {hi:g}% — trim to ~{hi:g}% "
                                   f"({money(r['val'] - total*hi/100.0)} to sell)")
            elif w < lo:
                verdict = "below band"
                rerate_add.append(f"{r['sym']} {w:.1f}% below {lt} bottom {lo:g}% — add (if a route qualifies) "
                                  f"or the tier is wrong; say which")
            elif w > hi:
                verdict = f"gap (≤{tol:g}pt tol)"
                rerate_declare.append(f"{r['sym']} {w:.1f}% sits above {lt} top {hi:g}% but inside the {tol:g}pt "
                                      f"tolerance — DECLARE the tier it deserves, do not trade it")
            else:
                verdict = "in band"
        r["c0b"] = verdict
        add(f"| {r['sym']} | {lt or '—'} | {w:.1f} | {r['wt']:.1f} | {money(r['val'])} | "
            f"{r['pl_pct']:+.1f} | {r['day_pct']:+.1f} | {verdict} | {rv} |")

    add("")
    add("### §C-0b conviction re-rating (account basis — the tier band IS the target weight)")
    if rerate_untiered:
        fail("LIVE_TIER_MISSING",
             "no live tier on: " + ", ".join(rerate_untiered) + " — §C-0b says 'legacy'/null is not acceptable",
             "high", False)
        add(f"- ⚠ **NO LIVE TIER:** {', '.join(rerate_untiered)} — score them this cycle.")
    for m in rerate_trim:
        fail("RERATE_TRIM", m, "high", False)
        add(f"- ⛔ **TRIM REQUIRED:** {m}")
    for m in rerate_add:
        add(f"- ⬆ {m}")
    for m in rerate_declare:
        add(f"- 📌 {m}")
    if not (rerate_trim or rerate_add or rerate_declare or rerate_untiered):
        add("- ✅ every position inside its live tier band — no re-rating action.")
    add("- ⚠ a re-rating is justified by CONVICTION evidence, **never by P&L**. Re-rating changes SIZE; "
        "the thesis-exit trigger changes OWNERSHIP; neither may do the other's job.")

    # ---- risk (ATR) -------------------------------------------------------
    atr = collect_atr([r["sym"] for r in rows])
    risk_total = 0.0
    for r in rows:
        a = atr.get(r["sym"])
        r["atr_pct"] = (a / r["last"] * 100.0) if (a and r["last"]) else None
        r["risk"] = (r["val"] * r["atr_pct"] / 100.0) if r["atr_pct"] else None
        if r["risk"]:
            risk_total += r["risk"]

    # Risk % is only meaningful if ATR covers most of the book — a partial denominator
    # would silently overstate whichever names happen to have data.
    covered_val = sum(r["val"] for r in rows if r["risk"])
    coverage = (covered_val / eq * 100.0) if eq else 0.0
    risk_ok = coverage >= 80.0
    if atr and not risk_ok:
        missing = [r["sym"] for r in rows if not r["risk"]]
        warn(f"ATR covers only {coverage:.0f}% of equity — risk caps NOT evaluated. Missing: {', '.join(missing)}")

    bloc = set((pol.get("ai_bloc") or {}).get("members") or [])
    bloc_val = sum(r["val"] for r in rows if r["sym"] in bloc)
    bloc_pct = (bloc_val / eq * 100.0) if eq else 0.0
    bloc_risk = sum(r["risk"] or 0.0 for r in rows if r["sym"] in bloc)
    bloc_risk_pct = (bloc_risk / risk_total * 100.0) if (risk_total and risk_ok) else 0.0

    ai = pol.get("ai_bloc") or {}
    # The bloc's PRINTED NAME is configuration, not code. It was hard-coded to one
    # instance's theme, which a shared template cannot ship: postcheck's BLOC_LINE_MISSING
    # would then oblige every user to write that theme into their own journal every cycle.
    # `policy.ai_bloc.label` names yours; unset, the brief just says "BLOC".
    bloc_title = ((ai.get("label") or "").strip() + " BLOC").strip()
    add("")
    add("## Concentration")
    add(f"- **{bloc_title} {money(bloc_val)} = {bloc_pct:.1f}% of equity** (soft {ai.get('soft_cap_pct_equity')}% / hard {ai.get('hard_cap_pct_equity')}%)")
    if risk_total and risk_ok:
        add(f"- **bloc = {bloc_risk_pct:.1f}% of DAILY RISK** (soft {ai.get('soft_cap_pct_risk')}% / hard {ai.get('hard_cap_pct_risk')}%) · book risk ≈ {money(risk_total)}/day")
        add("- ⚠ risk share is the binding measure — a concentrated bloc's dollar weight understates it whenever the bloc is more volatile than the rest of the book.")
    elif not atr:
        warn("no ATR data — risk-denominated caps NOT evaluated this cycle (write bot/raw/atr_<SYM>.json for EVERY holding)")

    if bloc_pct >= num(ai.get("hard_cap_pct_equity"), 999):
        fail("BLOC_HARD_CAP", f"bloc {bloc_pct:.1f}% >= hard cap — TRIM most levered name back inside", "high", False)
    elif bloc_pct >= num(ai.get("soft_cap_pct_equity"), 999):
        fail("BLOC_SOFT_CAP", f"bloc {bloc_pct:.1f}% >= soft cap — NO new in-bloc buys", "high", False)
    if risk_total and risk_ok and bloc_risk_pct >= num(ai.get("hard_cap_pct_risk"), 999):
        fail("BLOC_RISK_HARD", f"bloc {bloc_risk_pct:.1f}% of risk >= hard cap", "high", False)

    # per-name bands
    bands = pol.get("bands") or {}
    lev = set(bands.get("levered_names") or [])
    for r in rows:
        cap = num(bands.get("levered_pct")) if r["sym"] in lev else num(bands.get("unlevered_pct"))
        if r["wt"] >= num(bands.get("hard_pct"), 999):
            fail("BAND_HARD", f"{r['sym']} {r['wt']:.1f}% >= {bands.get('hard_pct')}% hard ceiling", "high", False)
        elif r["wt"] >= cap:
            fail("BAND_BREACH", f"{r['sym']} {r['wt']:.1f}% >= {cap}% band — trim to ~{cap-3:.0f}%", "high", False)

    if rows and risk_total and risk_ok:
        top = sorted([r for r in rows if r["risk"]], key=lambda r: -r["risk"])[:3]
        add(f"- top risk contributors: " + " · ".join(
            f"**{r['sym']}** {money(r['risk'])}/day ({r['risk']/risk_total*100:.0f}%, ATR {r['atr_pct']:.1f}%)" for r in top))

    # ---- pre-commitments --------------------------------------------------
    add("")
    add("## Pre-commitments")
    for sym, pc in (state.get("precommitments") or {}).items():
        if pc.get("status") != "active":
            continue
        gate = num(pc.get("gate_price"))
        last = quotes.get(sym, {}).get("last")
        n = int(pc.get("observations_failed") or 0)
        limit = int(pol.get("precommit_expiry_observations") or 10)
        if last:
            hit = (last <= gate) if pc.get("direction") == "lte" else (last >= gate)
            gap = (last / gate - 1.0) * 100.0
            if hit:
                add(f"- 🔔 **{sym} GATE MET — {money(last)} vs {money(gate)}. ACTION: {pc.get('action')}** (re-verify gate ③ first)")
            else:
                add(f"- {sym} ${last:,.2f} vs gate ${gate:,.2f} — **fails by {gap:+.2f}%**, {n} consecutive failures")
                if n >= limit:
                    fail("PRECOMMIT_EXPIRED",
                         f"{sym} has failed {n} >= {limit} observations — RE-JUSTIFY from fresh fundamentals or RETIRE, in writing",
                         "high", False)
        else:
            warn(f"no quote for pre-commitment {sym} — gate NOT evaluated")

    # ---- roll-off warnings -------------------------------------------------
    today = dt.date.today()
    soon = []
    for src in ("bench", "holdings_highs"):
        for sym, d in (state.get(src) or {}).items():
            hd = d.get("high_date")
            if not hd:
                continue
            try:
                roll = dt.date.fromisoformat(hd) + dt.timedelta(days=365)
            except ValueError:
                continue
            days = (roll - today).days
            if 0 <= days <= 7:
                soon.append(f"**{sym}** high {money(num(d.get('high')))} rolls off in {days}d ({roll})")
    if soon:
        add("")
        add("## ⚠ 52-wk-high roll-off within 7 days — any gate change on these dates is a CALENDAR ARTIFACT, not a setup")
        for s in soon:
            add(f"- {s}")

    # ---- PASS-list expiry --------------------------------------------------
    due = []
    q = int(pol.get("pass_list_reexamine_quarters") or 2)
    for sym, d in ((state.get("pass_list") or {}).get("permanent") or {}).items():
        if not d:
            continue
        try:
            when = dt.date.fromisoformat(d) + dt.timedelta(days=91 * q)
        except ValueError:
            continue
        if today >= when:
            due.append(f"{sym} (print {d})")
    if due:
        add("")
        add(f"## PASS-list re-adjudication due — {', '.join(due)}")
        add("_Expiry forces a LOOK, never a buy._")

    # ---- cash posture ------------------------------------------------------
    # The deployment CLOCK was retired 2026-09-01 (owner directive). It set a cash
    # target with a deadline and a forcing backstop; the loop complied and deployed a
    # large share of the account on a calendar into a falling tape. Cash has NO target
    # and NO deadline — only an operational floor, which is a floor and not something
    # to move toward. Deliberately no DEPLOY_BACKSTOP failure exists any more: nothing
    # in this brief may tell a cycle it MUST buy.
    c = pol.get("cash") or {}
    retired = c.get("clock_retired")
    add("")
    add("## Cash posture")
    floor = max(num(c.get("floor_usd"), 50.0), total * num(c.get("floor_pct"), 5.0) / 100.0)
    if retired:
        add(f"- **No cash target, no deadline, no backstop** (clock retired {retired.get('date')}, "
            f"{retired.get('by')}). **Holding cash is a valid resting state and needs no justification.**")
        add(f"- cash {cash_pct:.1f}% · floor {money(floor)} (a FLOOR, not a target) · "
            f"spendable above floor **{money(max(0.0, bp - floor))}**")
        add("- ⛔ Do not reintroduce a cash target, deadline, session counter, or forcing backstop.")
    else:
        tgt = c.get("target_pct_max")
        add(f"- cash {cash_pct:.1f}%" + (f" vs target ≤{num(tgt):.0f}%" if tgt is not None else " · no target set"))
        add(f"- cash floor {money(floor)} · **deployable now: {money(max(0.0, bp - floor))}**")

    # ---- sizing -----------------------------------------------------------
    # tiers are % of TOTAL ACCOUNT (revised 2026-08-24) so they scale with the account
    tiers = pol.get("sizing_tiers_pct_account") or {}
    npos = len(rows)
    cap_n = int(pol.get("positions_soft_cap") or 10)
    min_pct = num(pol.get("min_new_position_pct_account"), 4.0)
    add("")
    add("## Sizing (declare TIER + reason BEFORE the order — % of TOTAL ACCOUNT)")
    for tname in ("TIER1", "TIER2", "TIER3"):
        lo, hi = (tiers.get(tname) or [0, 0])[:2]
        add(f"- **{tname}** {lo:g}–{hi:g}% of account = **{money(total*lo/100.0)}–{money(total*hi/100.0)}**")
    add("- ⛔ **a fill outside its declared tier's band FAILS postcheck. There is no default 'standard starter' size — the declared tier IS the size.**")
    add(f"- positions **{npos}/{cap_n}**" + (
        " — ⚠ **AT SOFT CAP: a NEW NAME must be ranked head-to-head against the weakest holding; "
        "if it wins, SELL THE WEAKEST AND TAKE IT. \"No action\" is an INVALID outcome here.**"
        if npos >= cap_n else ""))
    add(f"- minimum new position {min_pct:.0f}% of account = **{money(total * min_pct / 100.0)}**")

    # ---- add channel (§C-1) — the position cap binds NEW NAMES ONLY -------
    # ---- what is actually do-not-add, as of 2026-09-01 ------------------
    # WAS: `blocked = bloc` — the bloc's members hard-coded as do-not-add ahead of one
    # dated earnings print. That freeze was DATED and the date passed: the print landed
    # and beat, so the mandate's own pre-committed BEAT branch fired and re-enabled bloc
    # adds up to the soft cap. The brief kept printing the freeze for four cycles after
    # it expired, and an add was made in spite of it — i.e. the deterministic layer was
    # contradicting the decision it was supposed to be governing. A claim in the spec
    # outliving the fact it described.
    # Now derived, not dated: bloc names are blocked only when a bloc cap actually
    # binds, plus any name carrying its own `do_not_add` flag in state.
    bloc_capped = (bloc_pct >= num(ai.get("soft_cap_pct_equity"), 999)
                   or (risk_total and risk_ok
                       and bloc_risk_pct >= num(ai.get("soft_cap_pct_risk"), 999)))
    blocked = set(bloc) if bloc_capped else set()
    blocked |= {s for s, m in (state.get("positions") or {}).items()
                if isinstance(m, dict) and m.get("do_not_add")
                and m.get("status", "open") == "open"}
    block_reason = ("bloc cap binding" if bloc_capped else "per-name do-not-add rule")
    eligible = []
    for r in rows:
        if r["sym"] in blocked:
            continue
        cap = num(bands.get("levered_pct")) if r["sym"] in lev else num(bands.get("unlevered_pct"))
        room = (cap - r["wt"]) / 100.0 * eq  # $ before this name hits its band
        if room > 0:
            eligible.append((r["sym"], r["wt"], room))
    eligible.sort(key=lambda x: -x[2])
    add("")
    add("### Add channel (§C-1) — evaluated side-by-side with new names, NOT a backstop")
    if npos >= cap_n:
        add(f"- ⚠ **the {cap_n}-cap does NOT block adds** — it binds new NAMES only. Topping up an existing holding is open.")
    if blocked:
        add(f"- blocked ({block_reason}): **{', '.join(sorted(blocked))}**")
    if eligible:
        add("- eligible now: " + " · ".join(f"**{s}** ({w:.1f}%, {money(rm)} to band)" for s, w, rm in eligible[:6]))
        r3_on = (pol.get("add_routes") or {}).get("ROUTE3_macro_weakness_thesis_intact", True)
        add("- an add qualifies via ANY ONE of the routes below — name the route in the Orders line:")
        add("  1. **CONFIRMING EVIDENCE** — a beat, a raise, a contract, a resolved uncertainty.")
        add("  2. **PRE-DECLARED SCALE-IN** — a tranche plan written AT ENTRY whose trigger has now hit. Execute, do not re-debate.")
        if r3_on:
            add("  3. **MACRO WEAKNESS, THESIS INTACT** — down on sector/macro/rate causes, nothing company-specific, "
                "falsifier restated in writing. Max TIER2, once per name per week, not if already at band.")
        else:
            _sus = (pol.get("add_routes") or {}).get("route3_suspended") or {}
            add(f"  3. ⛔ **ROUTE 3 (macro weakness) is SUSPENDED — {_sus.get('date','')} {_sus.get('by','')}. "
                f"DO NOT USE, do not re-enable without the owner.** {_sus.get('reason','')}")
            add("  ⚠ **An add now requires a COMPANY-SPECIFIC catalyst (R1) or a tranche written at entry (R2). "
                "A macro dip is not evidence — 'it is down on rates' is no longer a route.**")
        # R3 cooldown (added 2026-08-24): once per name per week is policy; make it VISIBLE.
        # Source of truth is state.positions[sym].last_route3, written by postcheck from the
        # broker's fills. It reads `last_route3` — NOT `last_add` — because last_add records
        # the most recent add of ANY route, so a route-1 or route-2 top-up landing inside the
        # week used to OVERWRITE the route-3 record and silently clear the cooldown early
        # (fixed 2026-08-26; `last_add` is kept as general history). Falls back to last_add so
        # names recorded before the split still cool down correctly.
        if r3_on and (pol.get("add_routes") or {}).get("route3_once_per_name_per_week", True):
            today = dt.date.today()
            cooling = []
            for s_, _w, _rm in eligible:
                p_ = ((state.get("positions") or {}).get(s_) or {})
                la = p_.get("last_route3") or p_.get("last_add") or {}
                if la.get("route") != 3 or not la.get("date"):
                    continue
                try:
                    used = dt.date.fromisoformat(la["date"])
                except Exception:
                    continue
                nxt = used + dt.timedelta(days=7)
                if today < nxt:
                    cooling.append(f"**{s_}** (R3 used {used:%-m/%-d}, next eligible {nxt:%-m/%-d})")
            if cooling:
                add("- ⛔ **ROUTE 3 ON COOLDOWN — once per name per week, and these have already used it: "
                    + " · ".join(cooling) + ". R1/R2 are still open for them; R3 is NOT.**")
            else:
                add("- R3 cooldown: clear — no name has used route 3 in the last 7 days.")
        add("- ⛔ still forbidden: adding on a BROKEN thesis, averaging down because it is red, or pure momentum. "
            "**If the only reason you can give is a price, it is a reflex, not an add.**")
        add(f"- ⚠ **\"no add qualified\" must now be evidenced NAME BY NAME across these {len(eligible)} — not asserted in aggregate.**")
        if risk_total and risk_ok and bloc_risk_pct >= num(ai.get("soft_cap_pct_risk"), 999):
            add(f"- 💡 bloc risk is **{bloc_risk_pct:.1f}%**, over its {ai.get('soft_cap_pct_risk')}% soft cap — "
                "**an add OUTSIDE the bloc is the only available action that LOWERS it.**")
    if risk_total and risk_ok and atr:
        add("- risk-sized guide (tier budget ÷ ATR%): a $150 tier-1 budget buys "
            + ", ".join(f"{s} {money(150.0/(atr[s]/quotes[s]['last']))}" for s in list(atr)[:2] if quotes.get(s, {}).get("last"))
            + " — size by RISK, not dollars.")

    # ---- orders reconciliation --------------------------------------------
    add("")
    add("## Orders since last cycle")
    if orders is None:
        warn("orders not fetched — broker-first reconciliation NOT performed")
    else:
        os_ = orders.get("orders") or []
        if not os_:
            add("- none — no other-runner activity")
        for o in os_[:10]:
            agent = o.get("placed_agent")
            tag = " ← **broker DRIP, not a loop action**" if agent == "drip" else ""
            amt = (o.get("dollar_based_amount") or {}).get("amount")
            add(f"- {o.get('symbol')} {o.get('side')} {o.get('state')} "
                f"{('$'+str(amt)) if amt else o.get('quantity')} @ {o.get('average_price')} · `{agent}`{tag}")
            if agent not in ("agentic", "drip", None):
                fail("UNEXPECTED_AGENT", f"order {o.get('id')} placed_agent={agent} — investigate before acting", "high", False)

    # ---- housekeeping ------------------------------------------------------
    jp = os.path.join(os.path.dirname(HERE), "JOURNAL.md")
    if os.path.exists(jp):
        sz = os.path.getsize(jp)
        limit = int(pol.get("journal_rotate_bytes") or 250000)
        if sz > limit:
            fail("JOURNAL_ROTATE", f"JOURNAL.md {sz:,}b > {limit:,}b — postcheck auto-rotates oldest cycles into JOURNAL_ARCHIVE.md at the end of this cycle (no script to run; bot/rotate.sh does not exist)", "low", True)

        # ---- prior cycle's status line (ADDED 2026-09-03, BACKPORT.md step 1a) ----
        # §3 of LOOP_PROMPT.md records a loop that once ran read-only for four days
        # unnoticed — a HOLD cycle and a blocked cycle looked identical, and nothing
        # checked whether the previous cycle's push or order path actually worked
        # before the next one trusted the journal and kept going. The status line
        # (§9) is the second line of the most recent `## CYCLE` entry: `state: … ·
        # order_path: … · push: …`. Read it and raise a REQUIRED ACTION if either
        # field explicitly says FAILED — this is what turns the "verify the push"
        # prose instruction in old §10 into something a cycle cannot walk past.
        # Deliberately silent when the prior entry HAS NO status line at all: every
        # entry that predates this feature has no such line, and firing on absence
        # would raise this required action on every cycle forever. Absence is
        # postcheck's STATUS_LINE_MISSING to catch on the cycle that wrote it, not
        # this check's business on the cycle that reads it back.
        try:
            with open(jp) as f:
                jtext = f.read()
        except Exception as e:
            jtext = None
            warn(f"could not read JOURNAL.md for prior-cycle status check: {e}")
        if jtext is not None:
            cyc_idx = [m.start() for m in re.finditer(r"^## CYCLE", jtext, re.M)]
            if cyc_idx:
                prior_lines = jtext[cyc_idx[-1]:].splitlines()
                prior_status = prior_lines[1] if len(prior_lines) > 1 else ""
                order_failed = re.search(r"order_path:\s*FAILED", prior_status)
                push_failed = re.search(r"push:\s*FAILED", prior_status)
                if order_failed or push_failed:
                    fail("PRIOR_CYCLE_FAILED",
                         f"prior cycle's status line reads \"{prior_status.strip()}\" — "
                         + ("order_path" if order_failed else "")
                         + (" and " if order_failed and push_failed else "")
                         + ("push" if push_failed else "")
                         + " did not succeed last cycle; verify the pipe actually works "
                         "before trusting this one",
                         "high", False)

    # ---- required actions --------------------------------------------------
    # FIXED 2026-09-01 15:45. `prior` is BY CONSTRUCTION the set of carried codes that did
    # NOT reproduce against this cycle's live broker fetch — yet every one of them was
    # printed as a 🚨 REQUIRED ACTION, and the ESCALATE banner fired *only* on that list.
    # So the loudest section of the brief was populated exclusively by findings the same
    # script had just determined were no longer true, and the "fix the RULE, not the run"
    # banner could only ever fire on a finding that did not recur — the exact inversion of
    # what ESCALATE means. Measured when it was found: three carried codes
    # (NO_REVIEW_TRIGGER, LIVE_TIER_MISSING, RERATE_TRIM) all named positions the broker
    # does not hold or a weight the broker contradicts, and the RERATE_TRIM row demanded a
    # sale on a 15.3% weight that live data puts at 9.9% — BELOW its band. In a
    # closed system (§5) an unnecessary sale is unrecoverable capital. Second false-trim
    # near-miss in one day; the 12:45 cycle caught the first (tier-weight basis).
    # A code that no longer reproduces is now reported as STALE and left for postcheck to
    # close. Conservative guard: if the inputs a check depends on were NOT read cleanly,
    # non-reproduction proves nothing, so those codes keep carrying as REQUIRED ACTIONS.
    DEGRADED = {"RAW_MISSING", "RAW_MALFORMED", "STATE_UNREADABLE", "PRECHECK_CRASHED"}
    cur = {f["code"] for f in FAIL}
    inputs_clean = not (cur & DEGRADED)
    carried = [p for p in read_open_failures() if p.get("code") not in cur]
    stale = [p for p in carried if inputs_clean]
    unverified = [] if inputs_clean else carried
    prior_occ = {p["code"]: p.get("occurrences", 1) for p in read_open_failures()}
    add("")
    if FAIL or unverified:
        add("## 🚨 REQUIRED ACTIONS — resolve or explicitly justify EACH in this cycle's entry")
        for f in FAIL:
            n = prior_occ.get(f["code"], 0) + 1
            add(f"- **[{f['code']}]**{f' (recurring, {n}× including this cycle)' if n > 1 else ''} {f['detail']}")
            if n >= 3:
                add("  - ⚠ **3rd+ recurrence — this rule is not working as written. Fix the RULE, not the symptom.**")
        for p in unverified:
            add(f"- **[{p['code']}] (carried, {p.get('occurrences',1)}× — UNVERIFIED this cycle)** {p['detail']}")
            add("  - ⚠ inputs were not read cleanly, so non-reproduction proves nothing — still open.")
    else:
        add("## ✅ No blocking findings")

    if stale:
        add("")
        add("## ℹ️ Stale carried findings — NO LONGER REPRODUCE against this cycle's live broker fetch")
        add("**Not action items.** Verified against live data this run; postcheck closes them at `--commit`. "
            "⛔ Do NOT trade to satisfy one — a carried row is a claim, the live fetch is the fact.")
        for p in stale:
            add(f"- ~~[{p['code']}] ({p.get('occurrences',1)}× open)~~ {p['detail']}")

    if WARN:
        add("")
        add("## Warnings (non-blocking)")
        for w in WARN:
            add(f"- {w}")

    return "\n".join(L) + "\n"


def read_open_failures() -> list[dict]:
    """Unresolved failures from prior cycles, collapsed by code.

    `occurrences` counts distinct CYCLES, not ledger rows. FIXED 2026-08-26 15:45.
    postcheck.open_codes() was corrected to de-duplicate by cycle earlier the same
    day, with a comment naming the exact hazard; precheck was left row-counting —
    so the fix landed on the counter nothing reads and missed the one that PRINTS
    the escalation banner. Re-running postcheck while trimming an entry appends a
    row per run, and the ENTRY_OVERSIZE carry actively forces those re-runs, so the
    tally inflated fastest on precisely the rule most likely to be re-run.
    Measured today: ENTRY_OVERSIZE read "12x" from 12 rows spanning 2 cycles.
    That is below the >=3 ESCALATE threshold, yet the banner fired and the 12:40
    cycle rewrote the entry-budget rule wholesale on it — introducing a 3,000b
    LIGHT base it recorded as "a number I invented today with no evidence behind
    it." ESCALATE means "the RULE is wrong, not the run"; on an inflated gauge it
    retires rules that have barely failed. Count cycles."""
    if not os.path.exists(LEDGER):
        return []
    seen: dict[str, dict] = {}
    cycles: dict[str, set] = {}
    try:
        with open(LEDGER) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                r = json.loads(line)
                c = r.get("code")
                if r.get("resolved"):
                    seen.pop(c, None)
                    cycles.pop(c, None)
                else:
                    # a re-run of the same cycle is the SAME occurrence
                    cycles.setdefault(c, set()).add(r.get("cycle") or r.get("ts"))
                    if c in seen:
                        seen[c]["detail"] = r.get("detail", seen[c]["detail"])
                    else:
                        seen[c] = r
                    seen[c]["occurrences"] = len(cycles[c])
    except Exception as e:
        WARN.append(f"failure ledger unreadable: {e}")
    return list(seen.values())


def append_ledger(entries: list[dict]) -> None:
    if not entries:
        return
    ts = dt.datetime.now(dt.timezone.utc).isoformat()
    with open(LEDGER, "a") as f:
        for e in entries:
            f.write(json.dumps({**e, "ts": ts, "resolved": False, "source": "precheck"}) + "\n")


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--brief", default=os.path.join(HERE, "brief.md"))
    args = ap.parse_args()

    try:
        with open(STATE) as f:
            state = json.load(f)
    except Exception as e:
        # A missing/corrupt state file must not silently disable every check.
        msg = (f"# PRECHECK BRIEF\n\n## 🚨 STATE UNREADABLE\n\n`bot/state.json`: {e}\n\n"
               "**Run the cycle MANUALLY against LOOP_PROMPT.md and repair state.json before trading.**\n")
        with open(args.brief, "w") as f:
            f.write(msg)
        append_ledger([{"code": "STATE_UNREADABLE", "detail": str(e), "severity": "critical", "auto_fixable": False}])
        print(msg)
        return 2

    try:
        out = build(state)
    except Exception:
        tb = traceback.format_exc(limit=6)
        out = ("# PRECHECK BRIEF\n\n## 🚨 PRECHECK CRASHED — checks did NOT run\n\n"
               f"```\n{tb}\n```\n**Fall back to LOOP_PROMPT.md manually this cycle. Do not assume gates passed.**\n")
        append_ledger([{"code": "PRECHECK_CRASH", "detail": tb.splitlines()[-1][:300], "severity": "critical", "auto_fixable": False}])

    with open(args.brief, "w") as f:
        f.write(out)
    append_ledger(FAIL)
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
