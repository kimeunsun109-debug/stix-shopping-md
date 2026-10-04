# OneDrive 다시제작 폴더에 두고 실행 — 저장소: Desktop\쇼핑몰관리md
$Repo = "$env:USERPROFILE\OneDrive\Desktop\쇼핑몰관리md"
if (-not (Test-Path $Repo)) {
  $Repo = "$env:USERPROFILE\OneDrive\Desktop\stix-shopping-md"
}
if (-not (Test-Path $Repo)) { throw "쇼핑몰관리md 저장소를 찾을 수 없습니다. git pull 후 다시 실행하세요." }
& "$Repo\detail_image\scripts\Start-GeminiLocal.ps1"
