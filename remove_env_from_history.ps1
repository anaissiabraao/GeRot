# Script para remover .env do histórico do Git usando BFG Cleaner
# ATENÇÃO: Este script reescreve o histórico do Git!

Write-Host "=== Removendo .env do histórico do Git ===" -ForegroundColor Yellow
Write-Host ""

# 1. Fazer backup
Write-Host "1. Criando backup..." -ForegroundColor Cyan
$backupPath = "C:\Users\Dell\GeRot_backup_$(Get-Date -Format 'yyyyMMdd_HHmmss')"
Copy-Item -Path "C:\Users\Dell\GeRot" -Destination $backupPath -Recurse -Force
Write-Host "   Backup criado em: $backupPath" -ForegroundColor Green
Write-Host ""

# 2. Baixar BFG Cleaner (se não existir)
$bfgPath = "C:\Users\Dell\bfg-1.14.0.jar"
if (-not (Test-Path $bfgPath)) {
    Write-Host "2. Baixando BFG Cleaner..." -ForegroundColor Cyan
    Invoke-WebRequest -Uri "https://repo1.maven.org/maven2/com/madgag/bfg/1.14.0/bfg-1.14.0.jar" -OutFile $bfgPath
    Write-Host "   BFG baixado com sucesso!" -ForegroundColor Green
} else {
    Write-Host "2. BFG já existe, pulando download..." -ForegroundColor Green
}
Write-Host ""

# 3. Remover .env do histórico
Write-Host "3. Removendo .env do histórico..." -ForegroundColor Cyan
Set-Location "C:\Users\Dell\GeRot"
java -jar $bfgPath --delete-files .env
Write-Host ""

# 4. Limpar refs e garbage collect
Write-Host "4. Limpando referências antigas..." -ForegroundColor Cyan
git reflog expire --expire=now --all
git gc --prune=now --aggressive
Write-Host ""

# 5. Force push (CUIDADO!)
Write-Host "5. ATENÇÃO: Você precisa fazer force push para atualizar o GitHub:" -ForegroundColor Red
Write-Host "   git push origin --force --all" -ForegroundColor Yellow
Write-Host ""
Write-Host "=== Processo concluído! ===" -ForegroundColor Green
Write-Host ""
Write-Host "PRÓXIMOS PASSOS:" -ForegroundColor Yellow
Write-Host "1. Trocar senha do PostgreSQL no Supabase" -ForegroundColor White
Write-Host "2. Atualizar variável DATABASE_URL no Render" -ForegroundColor White
Write-Host "3. Executar: git push origin --force --all" -ForegroundColor White
Write-Host "4. Verificar no GitHub se .env foi removido" -ForegroundColor White
