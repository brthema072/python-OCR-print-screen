param(
    [switch]$PularInstalacao,
    [switch]$SemInstalador,
    [string]$Versao = "1.0.0"
)

$ErrorActionPreference = "Stop"
$Raiz = Split-Path -Parent $PSScriptRoot
Set-Location $Raiz

$Versao = $Versao.Trim()
if ($Versao -notmatch "^\d+\.\d+\.\d+$") {
    throw "Versao invalida '$Versao'. Use o formato MAJOR.MINOR.PATCH, por exemplo 1.0.1."
}

$Python = Join-Path $Raiz ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    $comandoPython = Get-Command python -ErrorAction SilentlyContinue
    if (-not $comandoPython) {
        throw "Python nao encontrado. Crie o .venv e instale requirements-dev.txt."
    }
    $Python = $comandoPython.Source
}

if (-not $PularInstalacao) {
    Write-Host "[build] Instalando dependencias de desenvolvimento..."
    & $Python -m pip install --disable-pip-version-check -r (Join-Path $Raiz "requirements-dev.txt")
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao instalar as dependencias de desenvolvimento."
    }
}

# Prefere a instalacao em Program Files. No GitHub Actions, o Chocolatey cria
# um atalho em C:\ProgramData\chocolatey\bin, mas os dados ficam na pasta real.
$Tesseract = $null
$candidatosTesseract = @(
    (Join-Path ${env:ProgramFiles} "Tesseract-OCR\tesseract.exe"),
    (Join-Path ${env:ProgramFiles(x86)} "Tesseract-OCR\tesseract.exe")
)
foreach ($candidato in $candidatosTesseract) {
    if (Test-Path $candidato) {
        $Tesseract = $candidato
        break
    }
}
if (-not $Tesseract) {
    $comandoTesseract = Get-Command tesseract -ErrorAction SilentlyContinue
    if ($comandoTesseract) {
        $Tesseract = $comandoTesseract.Source
    }
}
if (-not $Tesseract -or -not (Test-Path $Tesseract)) {
    throw "Tesseract nao encontrado. Instale com: winget install --id UB-Mannheim.TesseractOCR"
}

$TesseractDir = Split-Path -Parent $Tesseract
$Tessdata = Join-Path $TesseractDir "tessdata"
if (-not (Test-Path $Tessdata)) {
    throw "Pasta tessdata nao encontrada em $TesseractDir."
}

$Idiomas = (& $Python -c "from ocr_captura.configuracao import IDIOMAS_TESSERACT; print(IDIOMAS_TESSERACT)").Trim()
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrWhiteSpace($Idiomas)) {
    throw "Nao foi possivel ler IDIOMAS_TESSERACT de configuracao.py."
}
$Tags = @(
    $Idiomas -split "\+" |
        ForEach-Object { $_.Trim() } |
        Where-Object { $_ } |
        Select-Object -Unique
)
if ($Tags.Count -eq 0) {
    throw "IDIOMAS_TESSERACT esta vazio."
}
$Tags += "osd"
$Tags = @($Tags | Select-Object -Unique)

foreach ($tag in $Tags) {
    $arquivo = Join-Path $Tessdata "$tag.traineddata"
    if (-not (Test-Path $arquivo)) {
        throw "Idioma '$tag' ausente em $Tessdata. Instale o idioma no Tesseract antes do build."
    }
}

$Staging = Join-Path $Raiz "build\tesseract"
Remove-Item $Staging -Recurse -Force -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Path (Join-Path $Staging "tessdata") -Force | Out-Null

Copy-Item $Tesseract $Staging
Copy-Item (Join-Path $TesseractDir "*.dll") $Staging
foreach ($tag in $Tags) {
    Copy-Item (Join-Path $Tessdata "$tag.traineddata") (Join-Path $Staging "tessdata")
}
$Licenca = $null
foreach ($candidatoLicenca in @(
    (Join-Path $TesseractDir "doc\LICENSE"),
    (Join-Path $TesseractDir "LICENSE")
)) {
    if (Test-Path $candidatoLicenca) {
        $Licenca = $candidatoLicenca
        break
    }
}
if ($Licenca) {
    Copy-Item $Licenca (Join-Path $Staging "LICENSE")
} else {
    Write-Warning "Licenca do Tesseract nao encontrada em $TesseractDir."
}

# Valida a copia portatil antes de empacotar. O TESSDATA_PREFIX aponta para a
# propria pasta tessdata para --list-langs devolver "por", nao "tessdata/por".
$env:TESSDATA_PREFIX = Join-Path $Staging "tessdata"
try {
    $listaLinguas = (& (Join-Path $Staging "tesseract.exe") --list-langs 2>&1) -join "`n"
    if ($LASTEXITCODE -ne 0) {
        throw "A copia portatil do Tesseract falhou em --list-langs."
    }
    foreach ($tag in $Tags) {
        if ($listaLinguas -notmatch "(?m)^$([regex]::Escape($tag))$") {
            throw "A copia portatil nao reconheceu o idioma '$tag'."
        }
    }
} finally {
    Remove-Item Env:TESSDATA_PREFIX -ErrorAction SilentlyContinue
}

$Icone = Join-Path $Raiz "empacotamento\ocr_capturas.ico"
if (-not (Test-Path $Icone)) {
    & $Python (Join-Path $Raiz "empacotamento\gerar_icone.py")
    if ($LASTEXITCODE -ne 0) {
        throw "Falha ao gerar o icone."
    }
}

# O version_info do PyInstaller exige uma tupla numerica de quatro partes.
$partesVersao = $Versao.Split(".")
$tuplaVersao = "$([int]$partesVersao[0]), $([int]$partesVersao[1]), $([int]$partesVersao[2]), 0"
$templateVersao = Join-Path $Raiz "empacotamento\version_info.txt"
$arquivoVersao = Join-Path $Raiz "build\version_info.txt"
New-Item -ItemType Directory -Force -Path (Join-Path $Raiz "build") | Out-Null
$conteudoVersao = Get-Content $templateVersao -Raw -Encoding UTF8
$conteudoVersao = $conteudoVersao.Replace("__VERSAO_TUPLA__", $tuplaVersao)
$conteudoVersao = $conteudoVersao.Replace("__VERSAO__", $Versao)
if ($conteudoVersao -match "__VERSAO") {
    throw "O template version_info.txt tem placeholders desconhecidos."
}
[System.IO.File]::WriteAllText(
    $arquivoVersao,
    $conteudoVersao,
    (New-Object System.Text.UTF8Encoding($false))
)

Remove-Item (Join-Path $Raiz "dist\OCR-Capturas") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $Raiz "build\pyinstaller") -Recurse -Force -ErrorAction SilentlyContinue
Remove-Item (Join-Path $Raiz "dist\instalador") -Recurse -Force -ErrorAction SilentlyContinue
Get-ChildItem (Join-Path $Raiz "dist") -Filter "OCR-Capturas-*-portable.zip" -ErrorAction SilentlyContinue |
    Remove-Item -Force -ErrorAction SilentlyContinue

Write-Host "[build] Executando PyInstaller..."
& $Python -m PyInstaller `
    --noconfirm `
    --clean `
    --distpath (Join-Path $Raiz "dist") `
    --workpath (Join-Path $Raiz "build\pyinstaller") `
    (Join-Path $Raiz "empacotamento\ocr_capturas.spec")
if ($LASTEXITCODE -ne 0) {
    throw "PyInstaller falhou."
}

$PastaApp = Join-Path $Raiz "dist\OCR-Capturas"
if (-not (Test-Path (Join-Path $PastaApp "OCR-Capturas.exe"))) {
    throw "O executavel nao foi gerado em $PastaApp."
}

$Zip = Join-Path $Raiz "dist\OCR-Capturas-$Versao-portable.zip"
Remove-Item $Zip -Force -ErrorAction SilentlyContinue
Write-Host "[build] Criando pacote portatil..."
$zipCriado = $false
for ($tentativa = 1; $tentativa -le 3; $tentativa++) {
    try {
        Compress-Archive -Path $PastaApp -DestinationPath $Zip -CompressionLevel Optimal
        $zipCriado = $true
        break
    } catch {
        Remove-Item $Zip -Force -ErrorAction SilentlyContinue
        if ($tentativa -eq 3) {
            throw "Falha ao criar o pacote portatil: $($_.Exception.Message)"
        }
        # O antivirus pode manter um arquivo aberto por alguns segundos.
        Write-Warning "ZIP bloqueado; tentando novamente em 3 segundos..."
        Start-Sleep -Seconds 3
    }
}
if (-not $zipCriado) {
    throw "Falha ao criar o pacote portatil."
}

if (-not $SemInstalador) {
    $Iscc = $null
    $comandoIscc = Get-Command iscc -ErrorAction SilentlyContinue
    if ($comandoIscc) {
        $Iscc = $comandoIscc.Source
    }
    if (-not $Iscc) {
        $caminhosIscc = @(
            (Join-Path $env:LOCALAPPDATA "Programs\Inno Setup 6\ISCC.exe"),
            (Join-Path ${env:ProgramFiles} "Inno Setup 6\ISCC.exe"),
            (Join-Path ${env:ProgramFiles(x86)} "Inno Setup 6\ISCC.exe")
        )
        foreach ($caminho in $caminhosIscc) {
            if (Test-Path $caminho) {
                $Iscc = $caminho
                break
            }
        }
    }
    if (-not $Iscc) {
        throw "Inno Setup 6 nao encontrado. Instale com 'winget install --id JRSoftware.InnoSetup' ou use -SemInstalador."
    }

    Write-Host "[build] Compilando o instalador..."
    New-Item -ItemType Directory -Force -Path (Join-Path $Raiz "dist\instalador") | Out-Null
    & $Iscc "/DMyAppVersion=$Versao" (Join-Path $Raiz "empacotamento\instalador.iss")
    if ($LASTEXITCODE -ne 0) {
        throw "Inno Setup falhou."
    }
}

Write-Host ""
Write-Host "Build concluido:"
Write-Host "  Executavel: $PastaApp\OCR-Capturas.exe"
Write-Host "  Portatil:   $Zip"
if (-not $SemInstalador) {
    Write-Host "  Instalador: $(Join-Path $Raiz "dist\instalador\OCR-Capturas-$Versao-instalador.exe")"
}
