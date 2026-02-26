import uuid
from app.auth import get_current_user, require_admin
from app.models import Bid, Market, RateChart, Result, Transaction, Wallet
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
# from ..auth import require_admin
import datetime

router = APIRouter(prefix="/api/admin", tags=["Market Result Management"])


# -----------------------------
# GAME RATES
# -----------------------------
GAME_RATES = {
    "single": 9,
    "jodi": 95,
    "single_panna": 140,
    "double_panna": 300,
    "triple_panna": 600,
    "half_sangam": 1200,
    "full_sangam": 10000,
}


# -----------------------------
# INPUT MODEL
# -----------------------------
class ResultDeclare(BaseModel):
    game_id: str
    date: str
    session: str  # open / close
    open_digit: str = None
    open_panna: str = None
    close_digit: str = None
    close_panna: str = None


# -----------------------------
# SETTLEMENT LOGIC
# -----------------------------
def settle_results(market_id: str, result_obj: Result):

    # Load rate chart
    chart = RateChart.objects().first()
    if not chart:
        print("Rate chart not found!")
        return

    open_digit = result_obj.open_digit
    close_digit = result_obj.close_digit
    open_panna = result_obj.open_panna
    close_panna = result_obj.close_panna

    bids = Bid.objects(market_id=market_id)

    # Rate chart mapping
    RATE_MAP = {
        "single": chart.single_digit_2,
        "jodi": chart.jodi_digit_2,
        "single_panna": chart.single_pana_2,
        "double_panna": chart.double_pana_2,
        "triple_panna": chart.tripple_pana_2,
        "half_sangam": chart.half_sangam_2,
        "full_sangam": chart.full_sangam_2,
    }

    for bid in bids:
        win = False

        # --------------------- WIN LOGIC ---------------------

        # SINGLE
        if bid.game_type == "single" and bid.digit == open_digit:
            win = True

        # JODI
        if bid.game_type == "jodi" and bid.digit == open_digit + close_digit:
            win = True

        # SINGLE PANNA
        if bid.game_type == "single_panna" and bid.digit == open_panna:
            win = True

        # DOUBLE PANNA
        if bid.game_type == "double_panna" and bid.digit == close_panna:
            win = True

        # TRIPLE PANNA
        if bid.game_type == "triple_panna":
            if bid.session == "open" and bid.digit == open_panna:
                win = True
            if bid.session == "close" and bid.digit == close_panna:
                win = True

        # HALF SANGAM – BOTH CASES SUPPORTED
        if bid.game_type == "half_sangam":
            panna, digitx = bid.digit.split("-")

            # Case 1 → open_panna + close_digit
            if panna == open_panna and digitx == close_digit:
                win = True

            # Case 2 → close_panna + open_digit
            if panna == close_panna and digitx == open_digit:
                win = True

        # FULL SANGAM
        if bid.game_type == "full_sangam":
            op, cp = bid.digit.split("-")
            if op == open_panna and cp == close_panna:
                win = True

        # --------------------- PAYOUT -------------------------
        if win:
            rate = RATE_MAP.get(bid.game_type, 0)
            amount = bid.points * rate

            wallet = Wallet.objects(user_id=bid.user_id).first()
            if wallet:
                wallet.update(inc__balance=amount)

                # Transaction log
                Transaction(
                    tx_id=str(uuid.uuid4()),
                    user_id=str(bid.user_id),
                    amount=amount,
                    payment_method="Win",
                    status="Approved"
                ).save()
@router.post("/result/declare")
def declare_result(payload: ResultDeclare, admin=Depends(require_admin)):
    session = payload.session.lower()

    market = Market.objects(id=payload.game_id).first()
    if not market:
        raise HTTPException(404, "Market not found")

    # Find or create today's result entry
    result = Result.objects(
        market_id=payload.game_id,
        date=payload.date
    ).first()

    if not result:
        result = Result(
            market_id=payload.game_id,
            date=payload.date,
            open_digit="-",
            close_digit="-",
            open_panna="-",
            close_panna="-",
        )

    now = datetime.datetime.now()

    # OPEN SESSION
    if session == "open":
        if not payload.open_digit and not payload.open_panna:
            raise HTTPException(400, "Open digit or panna required")

        result.open_digit = payload.open_digit or result.open_digit
        result.open_panna = payload.open_panna or result.open_panna
        result.open_declared_at = now

    # CLOSE SESSION
    elif session == "close":
        if not payload.close_digit and not payload.close_panna:
            raise HTTPException(400, "Close digit or panna required")

        result.close_digit = payload.close_digit or result.close_digit
        result.close_panna = payload.close_panna or result.close_panna
        result.close_declared_at = now

    else:
        raise HTTPException(400, "Session must be open or close")

    result.save()

    # SETTLE WINNERS
    settle_results(payload.game_id, result)

    return {"message": "Result declared successfully"}




# -----------------------------
# GET RESULTS BY DATE
# -----------------------------
@router.get("/results")
def get_results(date: str, admin=Depends(require_admin)):
    results = Result.objects(date=date)
    output = []

    for r in results:
        # fetch market name using the existing market schema
        market = Market.objects(id=r.market_id).first()

        output.append({
            "_id": str(r.id),
            "market_id": r.market_id,
            "game_name": market.name if market else "-",
            "date": r.date,
            "open_panna": r.open_panna,
            "open_digit": r.open_digit,
            "close_panna": r.close_panna,
            "close_digit": r.close_digit,
            "open_declared_at": getattr(r, "open_declared_at", None),
            "close_declared_at": getattr(r, "close_declared_at", None),
            "close_timne": market.close_time if market else "-",
            "open_time": market.open_time if market else "-",
        })

    return {"data": output}



# -----------------------------
# GET RESULT FOR GO BUTTON
# -----------------------------
@router.get("/result/find")
def find_result(date: str, game_id: str, session: str, admin=Depends(require_admin)):
    session = session.lower()
    r = Result.objects(market_id=game_id, date=date).first()

    if not r:
        return {"data": None}

    if session == "open":
        return {
            "data": {
                "open_panna": r.open_panna,
                "open_digit": r.open_digit
            }
        }

    elif session == "close":
        return {
            "data": {
                "close_panna": r.close_panna,
                "close_digit": r.close_digit
            }
        }

    else:
        raise HTTPException(400, "Invalid session")


@router.delete("/result/{result_id}")
def delete_result(result_id: str, admin=Depends(require_admin)):
    r = Result.objects(id=result_id).first()
    if not r:
        raise HTTPException(404, "Result not found")

    r.delete()
    return {"message": "Result deleted"}


@router.get("/win-history")
def win_history(user=Depends(get_current_user)):

    # Load rate chart
    chart = RateChart.objects().first()
    if not chart:
        raise HTTPException(500, "Rate chart not found")

    RATE_MAP = {
        "single": chart.single_digit_2,
        "jodi": chart.jodi_digit_2,
        "single_panna": chart.single_pana_2,
        "double_panna": chart.double_pana_2,
        "triple_panna": chart.tripple_pana_2,
        "half_sangam": chart.half_sangam_2,
        "full_sangam": chart.full_sangam_2,
    }

    bids = Bid.objects(user_id=str(user.id))
    win_data = []

    for bid in bids:

        # Find market
        market = Market.objects(id=bid.market_id).first()
        if not market:
            continue

        # Find declared result for that market+date
        result = Result.objects(market_id=bid.market_id, date=bid.date).first()
        if not result:
            continue

        win = False

        # Winning Logic (same as your settlement logic)
        if bid.game_type == "single" and bid.digit == result.open_digit:
            win = True

        if bid.game_type == "jodi" and bid.digit == result.open_digit + result.close_digit:
            win = True

        if bid.game_type == "single_panna" and bid.digit == result.open_panna:
            win = True

        if bid.game_type == "double_panna" and bid.digit == result.close_panna:
            win = True

        if bid.game_type == "triple_panna":
            if bid.session == "open" and bid.digit == result.open_panna:
                win = True
            if bid.session == "close" and bid.digit == result.close_panna:
                win = True

        if bid.game_type == "half_sangam":
            panna, digitx = bid.digit.split("-")
            if panna == result.open_panna and digitx == result.close_digit:
                win = True
            if panna == result.close_panna and digitx == result.open_digit:
                win = True

        if bid.game_type == "full_sangam":
            op, cp = bid.digit.split("-")
            if op == result.open_panna and cp == result.close_panna:
                win = True

        # If not win → skip
        if not win:
            continue

        # Calculate winning amount
        rate = RATE_MAP.get(bid.game_type, 0)
        win_amount = bid.points * rate

        # Fetch transaction (optional)
        tx = Transaction.objects(user_id=str(user.id), amount=win_amount).order_by('-id').first()

        win_data.append({
            "game_name": market.name,
            "game_type": bid.game_type,
            "points": bid.points,
            "digit_or_panna": bid.digit,
            "win_amount": win_amount,
            "date": bid.date,
            "session": bid.session,
            "declared_result": {
                "open_digit": result.open_digit,
                "open_panna": result.open_panna,
                "close_digit": result.close_digit,
                "close_panna": result.close_panna
            },
            "declared_time": {
                "open_declared_at": getattr(result, "open_declared_at", None),
                "close_declared_at": getattr(result, "close_declared_at", None),
            },
            "tx_id": tx.tx_id if tx else None
        })

    return {"wins": win_data}


