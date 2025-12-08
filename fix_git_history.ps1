# Script para limpar arquivos grandes do histórico do Git
# ATENÇÃO: Este script reescreve o histórico do Git

Write-Host "=" * 60 -ForegroundColor Cyan
Write-Host "LIMPANDO HISTÓRICO DO GIT - Arquivos Grandes" -ForegroundColor Yellow
Write-Host "=" * 60 -ForegroundColor Cyan

Write-Host "`n[OPÇÃO RECOMENDADA] Usar BFG Repo-Cleaner" -ForegroundColor Green
Write-Host "É mais rápido e seguro que git filter-branch"
Write-Host "`nPassos:"
Write-Host "1. Baixar BFG: https://rtyley.github.io/bfg-repo-cleaner/"
Write-Host "2. Executar: java -jar bfg.jar --delete-files '*.glb' ."
Write-Host "3. Executar: java -jar bfg.jar --delete-files '*.fbx' ."
Write-Host "4. Executar: git reflog expire --expire=now --all"
Write-Host "5. Executar: git gc --prune=now --aggressive"
Write-Host "6. Executar: git push origin main --force"

Write-Host "`n`n[OPÇÃO ALTERNATIVA] Reset e Force Push" -ForegroundColor Yellow
Write-Host "ATENÇÃO: Isso vai reescrever o histórico!"
Write-Host "`nDeseja continuar? (S/N): " -NoNewline -ForegroundColor Red

$response = Read-Host

if ($response -eq 'S' -or $response -eq 's') {
    Write-Host "`n[AÇÃO] Criando backup da branch atual..." -ForegroundColor Cyan
    git branch backup-before-cleanup
    Write-Host "[OK] Backup criado: backup-before-cleanup" -ForegroundColor Green
    
    Write-Host "`n[AÇÃO] Encontrando commit antes dos arquivos grandes..." -ForegroundColor Cyan
    # Commit antes de adicionar os arquivos grandes
    $safeCommit = "2fc719f"
    
    Write-Host "[INFO] Resetando para commit: $safeCommit" -ForegroundColor Yellow
    Write-Host "[INFO] Commits que serão perdidos:"
    git log --oneline "$safeCommit..HEAD"
    
    Write-Host "`nTem certeza? Isso vai APAGAR os commits acima! (S/N): " -NoNewline -ForegroundColor Red
    $confirm = Read-Host
    
    if ($confirm -eq 'S' -or $confirm -eq 's') {
        # Reset para o commit seguro
        git reset --hard $safeCommit
        
        # Re-adicionar as mudanças boas (sem os arquivos grandes)
        Write-Host "`n[AÇÃO] Re-adicionando arquivos..." -ForegroundColor Cyan
        git add .
        git commit -m "Add 3D viewer and room booking system (without large files)"
        
        Write-Host "`n[AÇÃO] Forçando push..." -ForegroundColor Cyan
        git push origin main --force
        
        Write-Host "`n[OK] Histórico limpo e push realizado!" -ForegroundColor Green
    } else {
        Write-Host "`n[CANCELADO] Nenhuma alteração foi feita" -ForegroundColor Yellow
    }
} else {
    Write-Host "`n[CANCELADO] Use a opção BFG Repo-Cleaner (mais segura)" -ForegroundColor Yellow
}

Write-Host "`n" -NoNewline
Write-Host "=" * 60 -ForegroundColor Cyan
