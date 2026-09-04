#!/usr/bin/env python3
"""
postcheck.py — validate the cycle that just ran, auto-fix what is mechanical,
and carry everything else into the NEXT cycle's brief as a blocking item.

    python3 bot/postcheck.py --cycle "2026-08-21 12:40"

This is the feedback loop. Three tiers of response:
  AUTO-FIX   mechanical drift (journal oversize) is repaired here, now.
  CARRY      behavioural misses become REQUIRED ACTIONS at the top of the next brief,
             where the model cannot miss them.
  ESCALATE   a failure recurring 3+ times means the RULE is wrong, not the run.
             It gets promoted to a loud banner for a human decision.

Exit codes: 0 clean · 1 findings carried · 2 postcheck itself failed.
"""

from __future__ import annotations
import json, os, re, sys, argparse, subprocess, datetime as dt, traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
STATE = os.path.join(HERE, "state.json")
LEDGER = os.path.join(HERE, "failures.jsonl")
JOURNAL = os.path.join(ROOT, "JOURNAL.md")

sys.path.insert(0, HERE)
import precheck as _pc  # noqa: E402 — re-run precheck's own checks to auto-resolve stale ledger rows

FOUND: list[dict] = []
FIXED: list[str] = []


def finding(code: str, detail: str, severity: str = "medium", auto_fixable: bool = False) -> None:
    FOUND.append({"code": code, "detail": detail, "severity": severity, "auto_fixable": auto_fixable})


def last_entry(text: str) -> tuple[str, bool]:
    """(block, is_cycle) for the final ## CYCLE / ## NOTE block.

    Compliance checks apply to CYCLE entries only — a NOTE is out-of-band commentary
    (an owner question, an audit) and must not be judged as if it were a trading cycle."""
    idx = [m.start() for m in re.finditer(r"^## (CYCLE|NOTE)", text, re.M)]
    if not idx:
        return "", False
    block = text[idx[-1]:]
    return block, block.lstrip().startswith("## CYCLE")


def load_state() -> dict:
    with open(STATE) as f:
        return json.load(f)


def ledger_rows() -> list[dict]:
    if not os.path.exists(LEDGER):
        return []
    out = []
    with open(LEDGER) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return out


def open_codes() -> dict:
    """code -> count of distinct CYCLES it is open on, unresolved only.

    Counts cycles, not ledger rows. Re-running postcheck on the same cycle appends
    another row for the same code (the ENTRY_OVERSIZE carry actively forces re-runs
    while you trim), so row-counting inflated the tally — one cycle trimmed over
    eight runs read as 'x8 chronic'. That matters: >=3 prints ESCALATE, whose whole
    meaning is 'the RULE is wrong, not the run', so an inflated count would tell a
    later cycle to retire a rule that had failed exactly once."""
    seen: dict[str, set] = {}
    for r in ledger_rows():
        c = r.get("code")
        if not c:
            continue
        if r.get("resolved"):
            seen.pop(c, None)
        else:
            seen.setdefault(c, set()).add(r.get("cycle") or r.get("ts"))
    return {c: len(v) for c, v in seen.items()}


def _declaration_for(entry: str, sym: str) -> tuple:
    """(tier, route) declared for `sym`, read from the text right after ITS OWN order line.

    A whole-entry `re.search` takes the first match in the file, which is why one entry
    resolved to route 2 out of a tranche plan stated further up, and another had seven
    "ROUTE n" strings to choose from.

    The window is FORWARD-ONLY from the `BUY <SYM>` token. Looking backwards re-created
    the very bug this replaced: a routes recap or a preceding order's declaration sitting
    above the order line got picked up instead (measured — in a two-order fixture the
    first order read as route 1 off a recap line, and the second read its TIER off the
    order above it). The journal convention puts the declaration after the symbol:
    "BUY <SYM> $230 — TIER 2 ... ROUTE 3".
    """
    for m in re.finditer(rf"\bBUY\s+{re.escape(sym)}\b", entry):
        w = entry[m.end(): m.end() + 260].split("\n\n")[0]
        mt = re.search(r"TIER\s*([123])", w, re.I)
        mr = re.search(r"(?:ROUTE|\bR)\s*([123])\b", w, re.I)
        if mt or mr:
            return (int(mt.group(1)) if mt else None,
                    int(mr.group(1)) if mr else None)
    return None, None


def _broker_buys(entry: str, ids_in_entry: set) -> tuple:
    """(buys, source, n_reconciled) — FILLED BUY orders this entry claims, from raw/orders.json.

    The broker is the source of WHAT HAPPENED; the entry is the source of the TIER and
    ROUTE declaration. orders.json is fetched with created_at_gte=<last cycle>, so it can
    legitimately contain earlier cycles' fills — the order ids recorded in the entry are
    what select this cycle's own. Falls back to prose when no id is present, so a cycle
    that forgets the id still gets checked (and gets ORDER_ID_NOT_JOURNALED).

    `n_reconciled` counts FILLED orders of ANY side whose id the entry records. Two bugs
    found 2026-09-02, both fired by the same sell-only cycle:
      (a) ORDER_ID_NOT_JOURNALED fired on a SELL-ONLY cycle. `buys` filters side=="buy",
          so a cycle that only sells always fell to the prose branch and carried the
          finding — even with the sell's id written in the Orders line. It was
          STRUCTURALLY unclearable: no prose could satisfy a check that only reads buys.
      (b) The prose fallback INVENTED a ticker. `BUY ([A-Z]{1,5})` matched the words
          "BUY LEG" in a sentence of the form "<SYM> BUY LEG — 9/03", so state.json recorded a
          position in "LEG" and then closed it. A fallback that parses English is exactly
          the prose-over-broker inversion the rest of this file exists to prevent, so it
          is now suppressed whenever the broker already reconciles the entry by id.
    """
    rows = []
    try:
        o = _pc.load("orders", required=False) or {}
        rows = o.get("orders") or []
    except Exception:
        rows = []

    buys, source = [], "broker"
    n_reconciled = sum(1 for r in rows
                       if r.get("state") == "filled" and r.get("id") in ids_in_entry)
    for r in rows:
        if r.get("side") != "buy" or r.get("state") != "filled":
            continue
        if r.get("id") not in ids_in_entry:
            continue
        amt = None
        dba = r.get("dollar_based_amount") or {}
        try:
            if dba.get("amount"):
                amt = float(dba["amount"])
            elif r.get("cumulative_quantity") and r.get("average_price"):
                amt = float(r["cumulative_quantity"]) * float(r["average_price"])
        except Exception:
            amt = None
        sym = r.get("symbol")
        tier, route = _declaration_for(entry, sym)
        buys.append({"symbol": sym, "amount": amt, "id": r.get("id"),
                     "tier": tier, "route": route})

    # Prose fallback ONLY when the broker reconciles nothing at all. If any filled order
    # in the entry is matched by id (a sell-only cycle included), the broker has already
    # said what happened and guessing tickers out of English can only add fiction — see
    # bugs (a) and (b) above.
    if not buys and not n_reconciled:
        e = entry
        m_sym = re.search(r"\bBUY\s+([A-Z]{1,5})\b", e)
        m_amt = re.search(r"BUY\b[^—\n]*?\$([\d,]+(?:\.\d+)?)", e)
        if m_sym and re.search(r"\*\*(?:BUY|SELL)\b|FILLED", e):
            sym = m_sym.group(1)
            tier, route = _declaration_for(e, sym)
            buys = [{"symbol": sym,
                     "amount": float(m_amt.group(1).replace(",", "")) if m_amt else None,
                     "id": None, "tier": tier, "route": route}]
            source = "prose"
    return buys, source, n_reconciled


def resolve(code: str, note: str) -> None:
    with open(LEDGER, "a") as f:
        f.write(json.dumps({
            "ts": dt.datetime.now(dt.timezone.utc).isoformat(),
            "code": code, "resolved": True, "detail": note, "source": "postcheck",
        }) + "\n")


def rotate_journal(limit: int) -> bool:
    """AUTO-FIX: move the oldest CYCLE blocks to the archive until under the limit.
    Never touches the header (everything above the first '## CYCLE') or any '## NOTE' —
    NOTE blocks are STEPPED OVER and left in place rather than blocking the rotation.

    Fixed 2026-08-28: the previous version refused any cut whose moved span contained a
    NOTE. Because a NOTE sat in the oldest span (2026-08-19), every candidate cut
    contained it, so rotation could never succeed and JOURNAL_ROTATE carried forever.
    Blocks are now selected individually, so a NOTE only pins itself."""
    try:
        with open(JOURNAL) as f:
            lines = f.readlines()
        starts = [i for i, l in enumerate(lines)
                  if l.startswith("## CYCLE") or l.startswith("## NOTE")]
        if not starts:
            return False
        header_end = starts[0]
        # (start, end, is_cycle) for every block, in file order
        blocks = [(s, starts[i + 1] if i + 1 < len(starts) else len(lines),
                   lines[s].startswith("## CYCLE"))
                  for i, s in enumerate(starts)]
        cycles = [b for b in blocks if b[2]]
        if len(cycles) < 6:
            return False

        # MEASURE BYTES, NOT CHARACTERS (fixed 2026-09-01). The caller gates on
        # os.path.getsize() — bytes — but this function used len(str), i.e. CHARACTERS.
        # The journal is dense with multi-byte glyphs (⭐ ⛔ ⚠ → …), so chars run ~2%
        # under bytes, and the file settled into a dead zone where
        #     char_count <= limit < byte_count
        # There, rotation stops early (thinking it is done) while the caller still sees
        # an oversize file, so the next run calls rotate again, the loop breaks
        # immediately with moving == [], and it returns False. JOURNAL_ROTATE then
        # carries FOREVER and escalates at 3 cycles. Same failure shape as NOTE
        # 2026-08-28g (rotation that could never succeed), different cause.
        nbytes = lambda ls: sum(len(l.encode("utf-8")) for l in ls)
        size = nbytes(lines)
        keep_newest = {id(b) for b in cycles[-5:]}   # always retain the last 5 cycles
        moving = []
        for b in blocks:
            if size <= limit:
                break
            if not b[2] or id(b) in keep_newest:
                continue                              # NOTEs and recent cycles stay put
            moving.append(b)
            size -= nbytes(lines[b[0]:b[1]])
        if not moving or size > limit:
            return False

        moved_idx = {i for b in moving for i in range(b[0], b[1])}
        moved = [lines[i] for i in sorted(moved_idx)]
        with open(os.path.join(ROOT, "JOURNAL_ARCHIVE.md"), "a") as f:
            f.write(f"\n## ROTATED {dt.date.today()} (auto, postcheck)\n\n")
            f.writelines(moved)
        with open(JOURNAL, "w") as f:
            f.writelines(lines[:header_end]
                         + [l for i, l in enumerate(lines[header_end:], header_end)
                            if i not in moved_idx])
        return True
    except Exception as e:
        finding("ROTATE_FAILED", f"auto-rotation error: {e}", "low", False)
        return False


def check(cycle: str, state: dict) -> None:
    pol = state.get("policy", {})

    if not os.path.exists(JOURNAL):
        finding("NO_JOURNAL", "JOURNAL.md missing", "critical")
        return
    with open(JOURNAL) as f:
        text = f.read()
    entry, is_cycle = last_entry(text)

    # 1. an entry was actually appended this cycle
    if not entry:
        finding("NO_ENTRY", "no ## CYCLE/## NOTE block found", "critical")
        return
    head = entry.splitlines()[0]
    if not is_cycle:
        print(f"last block is a NOTE, not a CYCLE — compliance checks skipped\n  {head[:70]}")
        return

    # 2. entry length.
    # REWRITTEN 2026-08-25 after ENTRY_OVERSIZE escalated at 3x (bot/README: "the rule is wrong,
    # not the run"). Rule 8 exists to stop the loop RE-TYPING unchanged reference data — PASS
    # lists, watch calendars, standing notes. It was instead firing on entries whose bulk was
    # (a) a real adjudication for a new position and (b) the standing sections the OWNER'S OWN
    # directives require verbatim every cycle (its coverage sections, its standing market
    # checks, the bloc line). Those are mandated restatement, not
    # boilerplate the loop chose, so the cap can never be met while they are counted — which is
    # a rule defect, not a discipline failure. The cap now measures DISCRETIONARY prose only.
    # This does NOT loosen rule 8's target: retyping an unchanged PASS list still counts.
    # REVISED 2026-08-26 after ENTRY_OVERSIZE escalated again at 5x. The 8/25 fix (exempt the
    # owner-mandated standing sections) was correct but insufficient: the cap was still a FLAT
    # per-entry number applied to a VARIABLE per-entry workload. A light HOLD cycle and a full
    # cycle that places an order and closes three carried adjudications on evidence were held to
    # the same 6,000b — so the cap penalised precisely the cycles that did the most work, and a
    # cheap HOLD could run at 6,000b of prose and pass. That is backwards. The cap is now a
    # BUDGET that scales with the cycle's actual workload, and it is TIGHTER than before for the
    # cycles rule 8 was aimed at (a light HOLD now gets 3,000b, not 6,000b).
    #   base      3,000b LIGHT (12:30) / 6,000b FULL
    #   +1,200b   per order recorded (the tier + route + falsifier record postcheck itself demands)
    #   +1,200b   per carried REQUIRED ACTION closed on evidence in this entry
    #   ceiling   9,000b, always
    # Retyping an unchanged PASS list, watch calendar, DST note or wash-sale note still counts in
    # full — rule 8's actual target is untouched. Backtested over 8/21-8/26: 4 of 8 entries still
    # fail, including the 8/24 12:45 light cycle that wrote 8,328b. Not a rubber stamp.
    ceiling = int(pol.get("entry_max_bytes_ceiling") or 9000)
    base_full = int(pol.get("entry_max_bytes") or 6000)
    base_light = int(pol.get("entry_max_bytes_light") or 3000)
    per_item = int(pol.get("entry_bytes_per_workload_item") or 1200)

    # The leading-marker tolerance matters: entries routinely write "⭐ **<LABEL> BLOC ...", and
    # the original `^\*\*` anchor did not match that — so the 8/25 exemption was silently
    # inoperative on exactly the line it was written for. Found 2026-08-26 (exempt read 0b).
    # The exempt list was incomplete, found 2026-08-26 by the same diagnosis 8/25 made one level
    # up: `**Portfolio:**` is required verbatim every cycle by CAPITAL DEPLOYMENT POLICY §A (live
    # buying power + unsettled + cash-as-%-of-account), `**Clock:**` by §C, and the light-cycle
    # skips line by RUNTIME rule 5. All three are directive-mandated restatement — the exact
    # category 8/25 created — but were being charged to the discretionary budget.
    # Deliberately NOT exempted: the §C-1 add-channel block. It is mandated too, but it is
    # ANALYSIS, and rule 8's pressure belongs on it.
    # ADDED 2026-09-03 (BACKPORT.md step 1a): the status line (LOOP_PROMPT.md §9) is
    # directive-mandated restatement exactly like the lines above, but it does not start
    # with `**` — it opens `state:` — so the existing anchor does not match it. Left out,
    # it would have been silently charged to the discretionary budget the same way the
    # 8/26 fix above found `**Portfolio:**` was: a real exemption that reads 0b.
    mandated = re.compile(
        r"^[⭐⚠🚨\s]*\*\*(Fidelity check|War-chest|Semi pulse|Tape / Semi pulse|Benchmark"
        r"|Portfolio|Clock|Light-cycle skips):\*\*.*$"
        r"|^[⭐⚠🚨\s]*\*\*[^*\n]*\bBLOC\b.*$"
        r"|^state:.*$",
        re.M)
    exempt = sum(len(m.group(0).encode()) for m in mandated.finditer(entry))
    size = len(entry.encode())
    discretionary = size - exempt

    is_light = bool(re.search(r"12:30 slot|—\s*LIGHT", head))
    n_orders = len(set(re.findall(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
                                  entry)))
    # Count the carried REQUIRED ACTIONS this entry was obliged to address, from the LEDGER —
    # not by grepping the entry for a marker phrase. A prose-matched counter silently paid 0
    # the moment an entry wrote "[X] RESOLVED" instead of "REQUIRED ACTION RESOLVED", i.e. the
    # budget moved with wording rather than with work. ENTRY_OVERSIZE is excluded: it IS this
    # check, and letting it fund its own budget is circular.
    n_closed = len([c for c in open_codes() if c != "ENTRY_OVERSIZE"])

    # Credit RULE/CODE WORK too, not only trades. Recommended by the 2026-08-31 15:30 cycle and
    # deferred to the owner; the 2026-09-02 decide-don't-escalate directive removed deferral as an
    # outcome, so it is decided here. The formula credited ONLY orders and closes, so a cycle whose
    # real output was a bug fix or a rule change earned ZERO budget for it — and the 09:45 entry
    # spent EIGHT trim iterations, demonstrably cutting analysis to fit (a swap-scoring datapoint
    # was deleted purely for bytes). The loop was spending judgment on byte-golf.
    # Counted from `git diff` — WORK ACTUALLY DONE — never from prose markers, for the same reason
    # n_closed is read from the ledger: a prose-matched counter moves with wording, not with work,
    # and here it would be trivially self-serving (write "FINDING", earn 1,200b).
    # state.json is excluded: postcheck writes it every cycle, so it would pay unconditionally.
    tracked = {"LOOP_PROMPT.md", "DECISIONS.md",
               "bot/postcheck.py", "bot/precheck.py", "bot/README.md"}
    try:
        changed = subprocess.run(["git", "diff", "--name-only", "HEAD"],
                                 capture_output=True, text=True, timeout=10,
                                 cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        n_fixes = len(tracked & set(changed.stdout.split()))
    except Exception:
        n_fixes = 0
    base = base_light if is_light else base_full
    # The CEILING still binds and is deliberately unchanged — this widens what earns budget, not
    # how much any entry may ever write, so it is not a rubber stamp.
    limit = min(ceiling, base + per_item * (n_orders + n_closed + n_fixes))
    budget = (f"{base:,}b {'LIGHT' if is_light else 'FULL'} base "
              f"+ {n_orders} order(s) + {n_closed} carried-item(s) closed "
              f"+ {n_fixes} spec/code file(s) changed = {limit:,}b")

    if discretionary > limit:
        finding("ENTRY_OVERSIZE",
                f"last entry {discretionary:,}b discretionary ({size:,}b total, {exempt:,}b "
                f"directive-mandated standing sections exempt) > {limit:,}b budget "
                f"[{budget}] — restate only what CHANGED (SELF-AUDIT rule 8)",
                "medium")
    else:
        resolve("ENTRY_OVERSIZE",
                f"{discretionary:,}b discretionary within budget [{budget}] "
                f"({size:,}b total, {exempt:,}b exempt)")

    # 3. ORDER CHECKS — sourced from the BROKER, one order at a time.
    #
    # REWRITTEN 2026-08-26 15:45. The prior version parsed a single order out of journal
    # PROSE with three whole-entry `re.search` calls that each took the FIRST match:
    #   m_route = ROUTE([123])   m_sym = BUY ([A-Z]{1,5})   m_tier = TIER([123])
    # Four defects, all measured against real entries in this journal, not hypothesised:
    #  (a) MULTI-ORDER BLINDNESS — a cycle placing two orders had only its FIRST validated
    #      and recorded. The second escaped the tier-size band check and never wrote a
    #      route-3 cooldown. It mattered on the cycle it was found: a large cash balance,
    #      a bloc freeze about to lift, and a deployment backstop wanting several entries
    #      inside a week.
    #  (b) FIRST-MATCH FRAGILITY — the 2026-08-24 12:45 entry contains SEVEN "ROUTE n"
    #      strings and got the right one only by ordering luck; another entry resolved to
    #      route=2 from its TRANCHE PLAN text, not from an add route.
    #  (c) ADD/ENTRY CONFLATION — a brand-new position wrote `last_add`, so a first buy
    #      whose prose merely MENTIONS route 3 would silently gate a legitimate add for 7d.
    #  (d) COOLDOWN ERASURE — `last_add` was the cooldown's only source, so a later route-1
    #      or route-2 add OVERWROTE the route-3 record and cleared the 7-day cooldown early.
    #      Route 3 now gets its own `last_route3` field that other routes cannot clobber.
    # Fix: enumerate FILLED BUYS from bot/raw/orders.json (broker truth, per the standing
    # broker-API-over-prose rule), match each to its own TIER/ROUTE declaration in a window
    # around that symbol, then validate and persist PER ORDER. Prose is now only the source
    # of the DECLARATION; the broker is the source of what actually happened.
    pol = state.get("policy") or {}
    tiers = pol.get("sizing_tiers_pct_account") or {}
    try:
        today = dt.date.fromisoformat(cycle[:10])
    except Exception:
        today = dt.date.today()

    ids_in_entry = set(re.findall(
        r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", entry))
    buys, orders_src, n_reconciled = _broker_buys(entry, ids_in_entry)
    placed = bool(buys) or bool(re.search(r"\*\*(?:BUY|SELL)\b|FILLED", entry))

    # An order the entry never names by id cannot be reconciled by a later cycle. The
    # broker file is fetched with created_at_gte=<last cycle>, so it legitimately holds
    # EARLIER cycles' fills too — the id is what distinguishes "mine" from "already
    # journalled". Flag prose that claims a fill with no id to back it.
    if orders_src == "prose" and placed:
        finding("ORDER_ID_NOT_JOURNALED",
                "this entry describes an order but records no order id, so it cannot be "
                "matched against get_equity_orders — falling back to prose parsing. "
                "Record the order id in the Orders line.", "medium")
    elif n_reconciled:
        resolve("ORDER_ID_NOT_JOURNALED",
                f"{n_reconciled} filled order id(s) reconciled against the broker "
                f"({len(buys)} buy(s))")

    if placed and not re.search(r"TIER\s*[123]", entry, re.I):
        finding("TIER_NOT_DECLARED",
                "an order appears in this entry with no TIER declared — §C-0 requires tier + reason BEFORE the order",
                "high")
    elif placed:
        resolve("TIER_NOT_DECLARED", "tier present")

    total = None
    if buys and tiers:
        try:
            # NB: _pc.load() already unwraps the MCP {"data": ...} envelope — do not index ["data"].
            total = float(_pc.load("portfolio", required=False)["total_value"])
        except Exception as e:
            finding("TIER_SIZE_UNCHECKED",
                    f"could not evaluate tier sizing (order WAS placed): {e.__class__.__name__}: {e}", "low")

    mismatches, sized_ok = [], []
    for b in buys:
        sym, amt, route, tier = b["symbol"], b["amount"], b["route"], b["tier"]

        # 3b. fill size must fall inside ITS OWN declared tier's band (added 2026-08-24).
        if total and tier and amt is not None:
            band = tiers.get(f"TIER{tier}")
            if band:
                lo, hi = total * band[0] / 100.0, total * band[1] / 100.0
                if not (lo * 0.95 <= amt <= hi * 1.05):  # 5% tolerance for fractional/market slippage
                    mismatches.append(
                        f"{sym} ${amt:,.2f} outside TIER{tier} (${lo:,.0f}-${hi:,.0f} = "
                        f"{band[0]:g}-{band[1]:g}% of ${total:,.2f})")
                else:
                    sized_ok.append(f"{sym} ${amt:,.2f} inside TIER{tier}")

        pos = state.setdefault("positions", {}).setdefault(sym, {})
        # (e) RE-ENTRY BLINDNESS — added 2026-09-03, found on a re-buy into a position
        # state said was closed.
        # `record_exits` (2026-08-31) gave the recorder an EXIT path but no way back IN, so
        # a buy into a name the loop had previously sold matched neither branch cleanly: the
        # stale `entry_date` made is_new False, and the fill was filed as an ADD to a record
        # still stamped `status: "closed"` / `exit_date`. Four consequences, all live in
        # state.json until this fix: (1) `tier` was never written, so precheck raised
        # LIVE_TIER_MISSING and Friday tier scoring had no tier for a position we hold;
        # (2) state claimed CLOSED while the broker showed the shares held — the
        # state-contradicts-broker inversion this file exists to prevent, and the same class
        # as the fabricated "LEG" ticker fixed 2026-09-02; (3) `entry_date`/`spy_at_entry`
        # stayed at the FIRST life's values, so §11's "return-on-cost vs the benchmark
        # since its own entry date" would have been computed from a window the position
        # did not exist in; (4) a fresh ENTRY was appended to `add_history`, double-counting
        # it in the route/tier scoring that decides whether tiering survives at all.
        # A buy into a closed position is a RE-ENTRY: treat it as an entry, but ARCHIVE the
        # prior life rather than overwrite it — §C-0c's prior-ownership check (added
        # 2026-09-02, after a loop nearly re-ran a two-name swap in reverse) reads this
        # record to detect round trips, so silently clearing exit_date would disable the
        # round-trip guard on exactly the name it was written for.
        reentry = bool(pos.get("exit_date") or pos.get("status") == "closed")
        is_new = (not pos.get("entry_date")
                  or pos.get("entry_date") == today.isoformat()
                  or reentry)

        # 3c. §C-1 ROUTE 3 cooldown — once per name per week (added 2026-08-24).
        # Route 3 is the macro-weakness route: repeating it inside a week is averaging
        # down on a schedule, which is exactly what the cap exists to stop.
        if route == 3 and not is_new:
            prev = pos.get("last_route3") or {}
            # A postcheck re-run must not flag this cycle's OWN add as its predecessor:
            # the record below is written by this same pass, and the ENTRY_OVERSIZE carry
            # actively forces re-runs. Match the exact cycle stamp, not the date — a
            # genuine second route-3 add to the same name in a LATER cycle on the same
            # day still trips the check (gap 0 < 7), as intended.
            if prev.get("cycle") == cycle:
                prev = {}
            if ((pol.get("add_routes") or {}).get("route3_once_per_name_per_week", True)
                    and prev.get("date")):
                try:
                    gap = (today - dt.date.fromisoformat(prev["date"])).days
                except Exception:
                    gap = None
                if gap is not None and gap < 7:
                    finding("R3_COOLDOWN_VIOLATED",
                            f"{sym} took a ROUTE 3 add {gap}d after its last one ({prev['date']}) — "
                            "§C-1 caps route 3 at once per name per week", "high")
                elif gap is not None:
                    resolve("R3_COOLDOWN_VIOLATED", f"{sym} last route-3 add {gap}d ago")

        rec = {"date": today.isoformat(), "cycle": cycle, "route": route,
               "tier": f"TIER{tier}" if tier else None, "amount": amt,
               "order_id": b.get("id")}
        if is_new:
            # A first buy is an ENTRY, not an add — it must not seed an add cooldown.
            # Persisting the tier here is what makes the Friday tier scoring possible at
            # all: §C-0 says tiering is RETIRED if Tier 1 does not out-return Tier 3, and
            # the 8/21 benchmark had to record tier_alpha_pts=null / "NOT SCORABLE"
            # because tiers were VALIDATED against fill size and then thrown away.
            if reentry:
                # Archive the closed life intact (round-trip guard reads it), then clear the
                # fields that would otherwise describe the OLD position as if it were this one.
                lives = pos.setdefault("prior_lives", [])
                lives.append({k: pos[k] for k in (
                    "entry_date", "exit_date", "exit_cycle", "lane", "tier", "spy_at_entry",
                    "last_add", "last_route3", "add_history") if pos.get(k) is not None})
                for k in ("exit_date", "exit_cycle", "status", "entry_date", "tier",
                          "spy_at_entry", "last_add", "last_route3", "add_history"):
                    pos.pop(k, None)
                FIXED.append(
                    f"recorded {sym} RE-ENTRY in state.json — archived life #{len(lives)} "
                    f"(held {lives[-1].get('entry_date')} → {lives[-1].get('exit_date')}) to "
                    "prior_lives and reopened the record; §C-0c round-trip guard still reads it")
            if tier:
                pos["tier"] = f"TIER{tier}"
            pos.setdefault("entry_date", today.isoformat())
            FIXED.append(f"recorded {sym} ENTRY tier {pos.get('tier')} in state.json — "
                         "Friday tier scoring now has data")
        else:
            pos["last_add"] = rec
            # Dedupe on order_id: postcheck is re-run on the SAME cycle by design
            # (README step 5a says to iterate the bare script while trimming), and a
            # blind append recorded the identical fill twice — once with route/tier
            # null from the first pass, once resolved from the second. That
            # double-counts the fill in the Friday tier/route scoring, i.e. it
            # corrupts the exact number §C-0 uses to decide whether tiering survives.
            # Found 2026-08-31 on a same-cycle add recorded twice. Last write wins: the later pass
            # has strictly better declaration data.
            hist = pos.setdefault("add_history", [])
            oid = rec.get("order_id")
            if oid:
                hist[:] = [h for h in hist if h.get("order_id") != oid]
            pos["add_history"] = hist + [rec]
            if route == 3:
                # dedicated field so a later route-1/2 add cannot clear the R3 cooldown
                pos["last_route3"] = rec
            FIXED.append(f"recorded {sym} route-{route} add ({rec['tier']}) in state.json — "
                         "R3 cooldown and tier scoring now have data to enforce against")

    if mismatches:
        finding("TIER_SIZE_MISMATCH",
                "; ".join(mismatches) + " — §C-0 sizes by tier, and the pre-8/24 $80–90 starter is retired",
                "high")
    elif sized_ok:
        resolve("TIER_SIZE_MISMATCH", "; ".join(sized_ok))

    # 4. Friday benchmark
    try:
        d = dt.date.fromisoformat(cycle[:10])
    except Exception:
        d = dt.date.today()
    is_close_slot = ("15:" in cycle) or ("16:" in cycle)
    if d.weekday() == 4 and is_close_slot:
        if not re.search(r"\*\*Benchmark", entry):
            finding("BENCHMARK_MISSING",
                    "Friday close cycle with no **Benchmark:** line — the mandate's own accountability test "
                    "(SELF-AUDIT rule 1). This is the rule that went unrun for ~40 cycles; do not let it lapse again.",
                    "high")
        else:
            resolve("BENCHMARK_MISSING", "benchmark line present")

    # 5. bloc line present. Keyed on the word BLOC alone, never on one instance's theme:
    # the label is `policy.ai_bloc.label` and a template cannot oblige a stranger to write
    # somebody else's noun into their journal to clear a finding.
    if not re.search(r"\bBLOC\b", entry, re.I):
        finding("BLOC_LINE_MISSING", "no BLOC line — required every cycle (SELF-AUDIT rule 2)", "medium")
    else:
        resolve("BLOC_LINE_MISSING", "bloc line present")

    # 6. live cash actually read
    if not re.search(r"buying[_ ]power", entry, re.I):
        finding("CASH_NOT_READ",
                "no buying power in the entry — every cycle must open on live cash (DEPLOYMENT POLICY §A)", "medium")
    else:
        resolve("CASH_NOT_READ", "live cash present")

    # 6a. status line present and well-formed (LOOP_PROMPT.md §9, ADDED 2026-09-03,
    # BACKPORT.md step 1a). §3 records a loop that once ran read-only for four days
    # unnoticed — a HOLD cycle and a blocked cycle look identical on a skim, and
    # nothing checked that the cycle's work actually reached GitHub or that the order
    # path worked. The status line is the second line of the entry, immediately after
    # the `## CYCLE` heading: `state: … · order_path: … · push: …`. This fires on all
    # three ways an entry can fail to actually say those things: the line missing
    # outright, a placeholder left in (`<state>`), or the bare template alternation
    # (`TRADED | HOLD | SKIPPED`) copied verbatim instead of one value chosen — every
    # one of those is indistinguishable from silence to precheck's PRIOR_CYCLE_FAILED
    # read next cycle, so this has to be strict about the exact three tokens.
    status_lines = entry.splitlines()
    status_line = status_lines[1].strip() if len(status_lines) > 1 else ""
    status_re = re.compile(
        r"^state:\s*(?:TRADED|HOLD|SKIPPED)\s*·\s*"
        r"order_path:\s*(?:OK|FAILED|NOT_TESTED)\s*·\s*"
        r"push:\s*(?:VERIFIED|FAILED)\s*$")
    if not status_re.match(status_line):
        finding("STATUS_LINE_MISSING",
                "no well-formed status line as the entry's second line (state/order_path/push — "
                "LOOP_PROMPT.md §9) — missing, a placeholder, or the template alternation left unresolved",
                "high")
    else:
        resolve("STATUS_LINE_MISSING", "status line present and well-formed")

    # 7. carried REQUIRED ACTIONS — auto-resolve anything precheck no longer reproduces,
    #    then flag only what's genuinely still open and unaddressed in this entry.
    POSTCHECK_OWNED = {"ENTRY_OVERSIZE", "TIER_NOT_DECLARED", "BENCHMARK_MISSING",
                        "BLOC_LINE_MISSING", "CASH_NOT_READ", "STATUS_LINE_MISSING"}
    try:
        current = {f["code"] for f in _pc.compute_failures(state)}
    except Exception as e:
        current = None  # re-check unavailable this run; fall back to "still open" for all
        finding("RECHECK_UNAVAILABLE", f"could not re-run precheck to auto-resolve stale codes: {e}", "low")

    for code, n in open_codes().items():
        if code in POSTCHECK_OWNED:
            continue
        if current is not None and code not in current:
            resolve(code, "auto-resolved — precheck no longer reproduces this finding")
            continue
        if code.lower().replace("_", " ").split()[0].lower() not in entry.lower() and code not in entry:
            finding("CARRIED_UNADDRESSED",
                    f"[{code}] was a REQUIRED ACTION ({n}× open) and is not referenced in this entry",
                    "high")

    # 8. AUTO-FIX journal size
    jlimit = int(pol.get("journal_rotate_bytes") or 250000)
    if os.path.getsize(JOURNAL) > jlimit:
        if rotate_journal(jlimit):
            FIXED.append(f"rotated JOURNAL.md to <{jlimit:,}b (oldest cycles → JOURNAL_ARCHIVE.md)")
            resolve("JOURNAL_ROTATE", "auto-rotated")
        else:
            finding("JOURNAL_ROTATE", f"JOURNAL.md over {jlimit:,}b and auto-rotation could not run", "low")

    print(f"cycle: {head[:70]}")


def record_exits(cycle: str, state: dict) -> None:
    """Mark state.positions entries the broker no longer holds as CLOSED.

    ADDED 2026-08-31. postcheck had an entry path and an add path but NO exit path, so a
    sold position kept its full live record in state.json forever. It went unnoticed
    because until today the loop had never closed a position since the tier/route
    machinery was built — a two-name swap was the first, i.e. the first moment this
    could bite.

    Why it matters and why this marks rather than deletes: precheck builds its position
    TABLE from the broker, so a stale row never showed up as a phantom holding — but the
    Friday tier/route scoring reads state.positions, and a name the account no longer owns
    would have been scored as if still held, with its entry price and no exit. That is the
    same class of corrupt-evidence bug as NOTE 2026-08-31a: a rule that retires itself on
    bad data is worse than no rule. Deleting the row would instead erase the closed trade
    from scoring entirely, which is the opposite error — a sleeve that only scores its
    survivors is marking its own homework. So: keep the record, stamp the exit, let the
    scorer decide.

    Broker-first, and silent when it cannot read: with no positions.json this returns
    without touching state, so a failed fetch can never mass-close the book.
    """
    try:
        raw = _pc.load("positions", required=False) or {}
    except Exception:
        return
    rows = raw.get("positions")
    if not rows:  # unreadable or empty -> do nothing, never infer an exit from absence
        return
    live = {r.get("symbol") for r in rows if r.get("symbol")}
    if not live:
        return
    today = cycle[:10]
    for sym, pos in (state.get("positions") or {}).items():
        if sym in live or not isinstance(pos, dict) or pos.get("exit_date"):
            continue
        pos["exit_date"] = today
        pos["exit_cycle"] = cycle
        pos["status"] = "closed"
        FIXED.append(f"recorded {sym} EXIT in state.json ({today}) — no longer held at the "
                     "broker; retained as a closed record so tier/route scoring keeps it")


def advance_deployment_clock(cycle: str, state: dict) -> None:
    """Recompute deployment_clock.sessions_elapsed from the calendar.

    ADDED 2026-08-26. `sessions_elapsed` was READ by precheck.py and written by NOTHING — it had
    been frozen at its hand-seeded value since 2026-08-21, so the deployment clock never advanced
    and its session-8 backstop (the one hard deadline in CAPITAL DEPLOYMENT POLICY §C) could never
    fire. Every "session N/15" in the journal was the model's own count, not state. Derive it
    instead: weekdays elapsed since clock.started, the start date counting as session 1.

    Market holidays are not modelled, so this can overcount by a day or so. That is the safe
    direction — it makes the backstop fire EARLIER, never later.
    """
    dc = state.get("deployment_clock") or {}
    if not dc.get("active") or not dc.get("started"):
        return
    try:
        start = dt.date.fromisoformat(str(dc["started"])[:10])
        today = dt.date.fromisoformat(cycle[:10])
    except Exception:
        return
    if today < start:
        return
    sessions = sum(1 for i in range((today - start).days + 1)
                   if (start + dt.timedelta(days=i)).weekday() < 5)
    if sessions != dc.get("sessions_elapsed"):
        FIXED.append(f"deployment clock: sessions_elapsed "
                     f"{dc.get('sessions_elapsed')} -> {sessions} (derived from calendar, "
                     f"clock started {start})")
    dc["sessions_elapsed"] = sessions
    state["deployment_clock"] = dc


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--cycle", default=dt.datetime.now().strftime("%Y-%m-%d %H:%M"))
    ap.add_argument("--commit", action="store_true", help="git-commit auto-fixes")
    args = ap.parse_args()

    try:
        state = load_state()
    except Exception as e:
        print(f"POSTCHECK: state unreadable: {e}", file=sys.stderr)
        return 2

    try:
        check(args.cycle, state)
    except Exception:
        traceback.print_exc()
        return 2

    # persist state cursor
    try:
        state["last_cycle"] = args.cycle
        record_exits(args.cycle, state)
        advance_deployment_clock(args.cycle, state)
        with open(STATE, "w") as f:
            json.dump(state, f, indent=2)
            f.write("\n")
    except Exception as e:
        print(f"warn: could not update state.json: {e}", file=sys.stderr)

    # write findings to the ledger so the NEXT precheck surfaces them
    if FOUND:
        ts = dt.datetime.now(dt.timezone.utc).isoformat()
        with open(LEDGER, "a") as f:
            for x in FOUND:
                f.write(json.dumps({**x, "ts": ts, "cycle": args.cycle,
                                    "resolved": False, "source": "postcheck"}) + "\n")

    counts = open_codes()
    print("\n=== POSTCHECK ===")
    for x in FIXED:
        print(f"  AUTO-FIXED : {x}")
    for x in FOUND:
        print(f"  CARRIED    : [{x['code']}] {x['detail'][:100]}")
    chronic = {c: n for c, n in counts.items() if n >= 3}
    if chronic:
        print("\n  *** ESCALATE — recurring 3+ cycles. The RULE is wrong, not the run. ***")
        for c, n in chronic.items():
            print(f"      [{c}] x{n} — rewrite or retire this rule in LOOP_PROMPT.md "
                  "(and record WHY in DECISIONS.md — a rule change edits both)")
    if not FOUND and not FIXED:
        print("  clean")

    if args.commit and FIXED:
        subprocess.run(["git", "add", "-A"], cwd=ROOT, check=False)
        subprocess.run(["git", "commit", "-q", "-m",
                        "postcheck: auto-fix — " + "; ".join(FIXED)], cwd=ROOT, check=False)

    return 1 if FOUND else 0


if __name__ == "__main__":
    sys.exit(main())
