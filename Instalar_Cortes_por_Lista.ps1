#requires -version 5.1
$ErrorActionPreference = "Stop"

# ============================================================
# INSTALADOR - CORTES POR LISTA V4.1
# Instala Python 3.12 e copia o script para o DaVinci Resolve.
# ============================================================

$ScriptFile = Join-Path $PSScriptRoot "Cortes_por_Lista_V4_1_Corrigida.py"

$Destino = "C:\ProgramData\Blackmagic Design\DaVinci Resolve\Fusion\Scripts\Utility"
$ArquivoDestino = Join-Path $Destino "Cortes_por_Lista_V4_1_Corrigida.py"

# Python 3.12 para Windows 64 bits
$PythonVersion = "3.12.9"
$PythonUrl = "https://www.python.org/ftp/python/$PythonVersion/python-$PythonVersion-amd64.exe"
$PythonInstaller = Join-Path $env:TEMP "python-$PythonVersion-amd64.exe"

# ------------------------------------------------------------
# ELEVAR PARA ADMINISTRADOR
# ------------------------------------------------------------

$principal = New-Object Security.Principal.WindowsPrincipal(
    [Security.Principal.WindowsIdentity]::GetCurrent()
)

$adminRole = [Security.Principal.WindowsBuiltInRole]::Administrator

if (-not $principal.IsInRole($adminRole)) {

    Write-Host "Solicitando permissao de administrador..." -ForegroundColor Yellow

    Start-Process powershell.exe `
        -Verb RunAs `
        -ArgumentList "-NoProfile -ExecutionPolicy Bypass -File `"$PSCommandPath`""

    exit
}

# ------------------------------------------------------------
# VERIFICAR ARQUIVO PRINCIPAL
# ------------------------------------------------------------

if (-not (Test-Path $ScriptFile)) {

    [System.Windows.Forms.MessageBox]::Show(
        "Arquivo Cortes_por_Lista_V4_1_Corrigida.py nao encontrado junto ao instalador.",
        "Erro no instalador"
    )

    throw "Arquivo principal nao encontrado."
}

# ------------------------------------------------------------
# VERIFICAR PYTHON 3.12
# ------------------------------------------------------------

$PythonExiste = $false

try {

    $versao = & py -3.12 --version 2>$null

    if ($LASTEXITCODE -eq 0 -and $versao -match "Python 3\.12") {
        $PythonExiste = $true
    }

}
catch {
    $PythonExiste = $false
}

# ------------------------------------------------------------
# INSTALAR PYTHON
# ------------------------------------------------------------

if (-not $PythonExiste) {

    Write-Host ""
    Write-Host "Python 3.12 nao encontrado." -ForegroundColor Yellow
    Write-Host "Baixando Python $PythonVersion..." -ForegroundColor Cyan

    try {

        Invoke-WebRequest `
            -Uri $PythonUrl `
            -OutFile $PythonInstaller `
            -UseBasicParsing

    }
    catch {

        throw "Nao foi possivel baixar o Python 3.12. Verifique sua conexao com a internet. Erro: $($_.Exception.Message)"
    }

    Write-Host "Instalando Python 3.12..." -ForegroundColor Cyan

    $Processo = Start-Process `
        -FilePath $PythonInstaller `
        -ArgumentList "/quiet InstallAllUsers=1 PrependPath=1 Include_test=0 Include_launcher=1" `
        -Wait `
        -PassThru

    if ($Processo.ExitCode -ne 0) {

        throw "A instalacao do Python terminou com codigo de erro: $($Processo.ExitCode)"
    }

    Start-Sleep -Seconds 3

    Write-Host "Python instalado com sucesso." -ForegroundColor Green

}
else {

    Write-Host "Python 3.12 ja esta instalado." -ForegroundColor Green
}

# ------------------------------------------------------------
# CRIAR PASTA DO DAVINCI
# ------------------------------------------------------------

Write-Host ""
Write-Host "Configurando pasta de scripts do DaVinci Resolve..." -ForegroundColor Cyan

if (-not (Test-Path $Destino)) {

    New-Item `
        -ItemType Directory `
        -Path $Destino `
        -Force | Out-Null
}

# ------------------------------------------------------------
# COPIAR SCRIPT
# ------------------------------------------------------------

Copy-Item `
    -Path $ScriptFile `
    -Destination $ArquivoDestino `
    -Force

if (-not (Test-Path $ArquivoDestino)) {

    throw "O arquivo nao foi copiado para a pasta do DaVinci Resolve."
}

# ------------------------------------------------------------
# CONCLUSÃO
# ------------------------------------------------------------

Write-Host ""
Write-Host "==============================================" -ForegroundColor Green
Write-Host " INSTALACAO CONCLUIDA COM SUCESSO!" -ForegroundColor Green
Write-Host "==============================================" -ForegroundColor Green
Write-Host ""
Write-Host "Arquivo instalado em:"
Write-Host $ArquivoDestino
Write-Host ""
Write-Host "Reinicie o DaVinci Resolve."
Write-Host "Depois acesse:"
Write-Host "Area de Trabalho > Scripts > Utility > Cortes_por_Lista_V4_1_Corrigida"
Write-Host ""

Add-Type -AssemblyName System.Windows.Forms

[System.Windows.Forms.MessageBox]::Show(
    "Instalacao concluida com sucesso!`n`nO script foi instalado em:`n$ArquivoDestino`n`nReinicie o DaVinci Resolve para atualizar a lista de scripts.",
    "Cortes por Lista V4.1",
    [System.Windows.Forms.MessageBoxButtons]::OK,
    [System.Windows.Forms.MessageBoxIcon]::Information
)

# Limpar instalador temporario do Python
if (Test-Path $PythonInstaller) {
    Remove-Item $PythonInstaller -Force -ErrorAction SilentlyContinue
}
