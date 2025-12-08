# Script para corrigir erro de push do GitHub
# Problema: Arquivos 3D muito grandes (>100MB)

Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "CORRIGINDO ERRO DE PUSH - Arquivos Grandes" -ForegroundColor Yellow
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan

# Opção 1: Usar Git LFS (Recomendado)
Write-Host "`n[OPÇÃO 1] Usar Git Large File Storage (LFS)" -ForegroundColor Green
Write-Host "Vantagens: Mantém arquivos no repositório, gerenciamento automático"
Write-Host "`nPassos:"
Write-Host "1. Instalar Git LFS: https://git-lfs.github.com/"
Write-Host "2. Executar comandos abaixo"

Write-Host "`n# Comandos para Git LFS:" -ForegroundColor Cyan
Write-Host "git lfs install"
Write-Host "git lfs track '*.glb'"
Write-Host "git lfs track '*.fbx'"
Write-Host "git add .gitattributes"
Write-Host "git add docs/Cd_front_12_50_53.glb"
Write-Host "git add docs/Cd_front_12_10_17.fbx"
Write-Host "git commit -m 'Add 3D models with Git LFS'"
Write-Host "git push origin main"

# Opção 2: Mover para static e adicionar ao .gitignore
Write-Host "`n`n[OPÇÃO 2] Mover arquivos para static e ignorar no Git" -ForegroundColor Green
Write-Host "Vantagens: Não sobe para GitHub, mantém local"
Write-Host "`nExecutando automaticamente...`n"

# Criar diretório se não existir
if (-not (Test-Path "static\docs")) {
    New-Item -ItemType Directory -Path "static\docs" -Force | Out-Null
    Write-Host "[OK] Diretório static\docs criado" -ForegroundColor Green
}

# Mover arquivos se existirem em docs/
if (Test-Path "docs\Cd_front_12_50_53.glb") {
    Move-Item "docs\Cd_front_12_50_53.glb" "static\docs\" -Force
    Write-Host "[OK] Arquivo GLB movido para static\docs\" -ForegroundColor Green
} else {
    Write-Host "[INFO] Arquivo GLB já está em static\docs\ ou não encontrado" -ForegroundColor Yellow
}

if (Test-Path "docs\Cd_front_12_10_17.fbx") {
    Move-Item "docs\Cd_front_12_10_17.fbx" "static\docs\" -Force
    Write-Host "[OK] Arquivo FBX movido para static\docs\" -ForegroundColor Green
} else {
    Write-Host "[INFO] Arquivo FBX já está em static\docs\ ou não encontrado" -ForegroundColor Yellow
}

# Atualizar .gitignore
Write-Host "`n[AÇÃO] Atualizando .gitignore..." -ForegroundColor Cyan

$gitignoreContent = @"

# Arquivos 3D grandes (não fazer upload para GitHub)
static/docs/*.glb
static/docs/*.fbx
docs/*.glb
docs/*.fbx
*.glb
*.fbx

# Outros arquivos grandes
*.zip
*.rar
*.7z
"@

Add-Content -Path ".gitignore" -Value $gitignoreContent
Write-Host "[OK] .gitignore atualizado" -ForegroundColor Green

# Remover arquivos do staging
Write-Host "`n[AÇÃO] Removendo arquivos grandes do Git..." -ForegroundColor Cyan
git rm --cached docs/Cd_front_12_50_53.glb 2>$null
git rm --cached docs/Cd_front_12_10_17.fbx 2>$null
git rm --cached static/docs/Cd_front_12_50_53.glb 2>$null
git rm --cached static/docs/Cd_front_12_10_17.fbx 2>$null
Write-Host "[OK] Arquivos removidos do staging" -ForegroundColor Green

# Commit das alterações
Write-Host "`n[AÇÃO] Fazendo commit das alterações..." -ForegroundColor Cyan
git add .gitignore
git commit -m "Update .gitignore to exclude large 3D files"
Write-Host "[OK] Commit realizado" -ForegroundColor Green

Write-Host "`n" -NoNewline
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan
Write-Host "CORREÇÃO CONCLUÍDA!" -ForegroundColor Green
Write-Host "=" -NoNewline -ForegroundColor Cyan
Write-Host ("=" * 59) -ForegroundColor Cyan

Write-Host "`nPróximos passos:" -ForegroundColor Yellow
Write-Host "1. Execute: " -NoNewline
Write-Host "git push origin main" -ForegroundColor Cyan
Write-Host "2. Os arquivos 3D ficarão apenas no seu computador local"
Write-Host "3. Para compartilhar os arquivos 3D, use Google Drive, Dropbox, etc."

Write-Host "`nOBS: Se preferir usar Git LFS, siga os comandos da OPÇÃO 1 acima" -ForegroundColor Yellow
