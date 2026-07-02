# GitHub 푸시 (1회)

로컬 커밋은 완료됨 (`main` 브랜치). GitHub CLI 로그인 후 아래만 실행하세요.

```powershell
cd "C:\Users\user\OneDrive\Desktop\쇼핑몰관리md"
gh auth login
gh repo create stix-shopping-md --public --description "STIX multi-mall MD" --source=. --remote=origin --push
```

이미 `origin`이 있으면:

```powershell
gh auth login
gh repo create stix-shopping-md --public --push
```

# Cursor Cloud 연결

1. https://cursor.com/dashboard → **Cloud Agents**
2. GitHub 계정 연결 → `stix-shopping-md` 저장소 선택
3. 새 Cloud Agent 실행 (브랜치 `main`)
4. `.cursor/environment.json` 이 Python + Playwright 자동 설치
5. **데이터**: Agent에 `쇼핑몰별 전체상품/` 폴더 엑셀 업로드 (OneDrive에서 복사)
6. **비밀번호**: Dashboard → Secrets (Wing 등, `.env.txt` 내용)

로컬 CDP(Chrome 9233) 스크래핑은 Cloud에서 불가 → 엑셀 export 후 분석 스크립트 사용.
