from http.server import BaseHTTPRequestHandler
from urllib.parse import urlparse, parse_qs, urlencode
import urllib.request, urllib.error
import json, os, time, hmac, hashlib, base64
from datetime import date, timedelta

OPENAPI = "https://openapi.naver.com"
SEARCHAD = "https://api.searchad.naver.com"


def _to_int(v):
    if isinstance(v, int): return v
    if isinstance(v, str):
        if "<" in v: return 5
        d = "".join(ch for ch in v if ch.isdigit())
        return int(d) if d else 0
    return 0


def _http(req, timeout=15):
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))


def fetch_trend(keyword):
    cid = os.environ["NAVER_CLIENT_ID"].strip()
    csec = os.environ["NAVER_CLIENT_SECRET"].strip()
    end = date.today().replace(day=1)
    start = (end - timedelta(days=31 * 12)).replace(day=1)
    body = {"startDate": start.isoformat(), "endDate": end.isoformat(), "timeUnit": "month",
            "keywordGroups": [{"groupName": keyword, "keywords": [keyword]}]}
    req = urllib.request.Request(OPENAPI + "/v1/datalab/search",
        data=json.dumps(body).encode("utf-8"),
        headers={"X-Naver-Client-Id": cid, "X-Naver-Client-Secret": csec, "Content-Type": "application/json"},
        method="POST")
    data = _http(req).get("results", [{}])[0].get("data", [])
    return [{"period": d["period"][:7], "ratio": round(d["ratio"], 1)} for d in data]


def _ad_sig(ts, method, path, secret):
    msg = f"{ts}.{method}.{path}"
    return base64.b64encode(hmac.new(secret.encode("utf-8"), msg.encode("utf-8"), hashlib.sha256).digest()).decode("utf-8")


def fetch_keywords(keyword):
    lic = os.environ["NAVER_AD_ACCESS_LICENSE"].strip()
    sec = os.environ["NAVER_AD_SECRET_KEY"].strip()
    cust = str(os.environ["NAVER_AD_CUSTOMER_ID"]).strip()
    method, path = "GET", "/keywordstool"
    ts = str(round(time.time() * 1000))
    hint = keyword.replace(" ", "")
    url = SEARCHAD + path + "?" + urlencode({"hintKeywords": hint, "showDetail": "1"})
    req = urllib.request.Request(url, headers={
        "Content-Type": "application/json; charset=UTF-8",
        "X-Timestamp": ts, "X-API-KEY": lic, "X-Customer": cust,
        "X-Signature": _ad_sig(ts, method, path, sec)}, method="GET")
    rows = _http(req).get("keywordList", [])
    out = []
    for x in rows:
        pc = _to_int(x.get("monthlyPcQcCnt")); mo = _to_int(x.get("monthlyMobileQcCnt"))
        out.append({"keyword": x.get("relKeyword", ""), "pc": pc, "mobile": mo,
                    "monthly": pc + mo, "comp": x.get("compIdx", "")})
    out.sort(key=lambda k: -k["monthly"])
    return out, hint.upper()


def diagnose(keyword):
    trend = fetch_trend(keyword)
    kws, target = fetch_keywords(keyword)
    exact = next((k for k in kws if k["keyword"].upper() == target), kws[0] if kws else None)
    if exact is None:
        exact = {"keyword": keyword, "pc": 0, "mobile": 0, "monthly": 0, "comp": "정보없음"}
    growth = 0
    if len(trend) >= 2 and trend[0]["ratio"] > 0:
        growth = round((trend[-1]["ratio"] - trend[0]["ratio"]) / trend[0]["ratio"] * 100)
    total = exact["monthly"] or 1
    device = {"pc": round(exact["pc"] / total * 100), "mobile": round(exact["mobile"] / total * 100)}
    related = [k for k in kws if k["keyword"].upper() != target][:14]
    if exact["monthly"] >= 30000:
        note = "검색량이 큰 핵심 키워드입니다. 경쟁이 치열하니 연관 롱테일 키워드로 진입 각을 만드는 전략이 유효합니다."
    elif growth > 25:
        note = "수요가 빠르게 성장하는 키워드입니다. 지금 콘텐츠·리뷰를 선점하면 효과가 큽니다."
    elif exact["monthly"] < 1000:
        note = "검색량이 작은 니치 키워드입니다. 전환 의도가 높은 타깃이라면 소규모 정밀 캠페인이 적합합니다."
    else:
        note = "안정적 수요가 있는 키워드입니다. 연관 키워드 묶음으로 노출 폭을 넓히는 접근을 권합니다."
    return {"keyword": keyword, "monthly_total": exact["monthly"], "monthly_pc": exact["pc"],
            "monthly_mobile": exact["mobile"], "comp_idx": exact["comp"], "growth_pct": growth,
            "device_split": device, "trend": trend, "related": related, "note": note}


class handler(BaseHTTPRequestHandler):
    def _send(self, code, payload):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        qs = parse_qs(urlparse(self.path).query)
        keyword = (qs.get("keyword", [""])[0]).strip()
        if qs.get("debug", [""])[0] == "1":
            def info(name):
                v = os.environ.get(name, ""); vs = v.strip()
                return {"exists": bool(v), "len": len(v), "len_stripped": len(vs),
                        "had_whitespace": v != vs, "tail": vs[-3:] if vs else ""}
            return self._send(200, {k: info(k) for k in
                ["NAVER_CLIENT_ID","NAVER_CLIENT_SECRET","NAVER_AD_ACCESS_LICENSE","NAVER_AD_SECRET_KEY","NAVER_AD_CUSTOMER_ID"]})
        if not keyword:
            return self._send(400, {"error": "keyword 파라미터가 필요합니다."})
        try:
            return self._send(200, diagnose(keyword))
        except urllib.error.HTTPError as e:
            detail = ""
            try: detail = e.read().decode("utf-8")[:300]
            except Exception: pass
            return self._send(502, {"error": f"네이버 API 오류 {e.code}", "detail": detail})
        except Exception as e:
            return self._send(500, {"error": f"{type(e).__name__}: {e}"})
