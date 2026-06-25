# 키워드 수요 진단 (Vercel)

네이버 데이터랩 + 검색광고 키워드도구로 키워드 수요·기회를 진단하는 단일 페이지 도구.
프론트(index.html) + 서버리스 함수(api/diagnose.py, 표준 라이브러리만). 키는 서버에만.

## 구조
```
index.html        프론트엔드 (정적)
api/diagnose.py   /api/diagnose?keyword=  서버리스 함수
vercel.json       라우팅
```

## 배포 (방법 1: GitHub + Vercel 대시보드 — 추천)
1. 이 폴더를 GitHub 저장소로 푸시
2. vercel.com → Add New → Project → 그 저장소 Import
3. **Settings → Environment Variables** 에 5개 등록 (.env.example 값):
   NAVER_CLIENT_ID, NAVER_CLIENT_SECRET,
   NAVER_AD_ACCESS_LICENSE, NAVER_AD_SECRET_KEY, NAVER_AD_CUSTOMER_ID
4. Deploy. 끝.

## 배포 (방법 2: CLI)
```bash
npm i -g vercel
vercel            # 첫 배포(프리뷰)
vercel env add NAVER_CLIENT_ID          # 5개 각각 등록
vercel env add NAVER_CLIENT_SECRET
vercel env add NAVER_AD_ACCESS_LICENSE
vercel env add NAVER_AD_SECRET_KEY
vercel env add NAVER_AD_CUSTOMER_ID
vercel --prod     # 운영 배포
```

## 동작
- index.html 은 /api/diagnose 를 호출. 실패하면 자동으로 데모 데이터로 폴백
  (환경변수 등록 전이나 미리보기에서도 화면이 보이게).
- 환경변수가 제대로 등록되면 실데이터로 동작.

## ⚠️ 보안
.env.example 의 키는 채팅에서 노출된 값이라 **운영 전 재발급** 권장.
재발급 후 Vercel 환경변수만 새 값으로 교체.

## 검색 점유율 기능 (선택, 나중에)
점유율·리뷰 발생 속도는 네이버 '검색 API'가 필요하다.
developers.naver.com → 서비스 API → 검색 → '오픈 API 이용 신청'으로 별도 발급 후
서버리스 함수에 검색 호출을 추가하면 확장 가능.
