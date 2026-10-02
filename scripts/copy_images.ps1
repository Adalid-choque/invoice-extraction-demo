$src = "D:\MAESTRÍA EN INGENIERÍA DE SOFTWARE AVANZADA 1V\Cursos\ARTIFICIAL INTELLIGENCE CAPSTONE PROJECT [Par. 1]\Tarea\Dataset"
$dst = "D:\MAESTRÍA EN INGENIERÍA DE SOFTWARE AVANZADA 1V\Cursos\ARTIFICIAL INTELLIGENCE CAPSTONE PROJECT [Par. 1]\Tarea\image-classification-demo\invoice-extraction-demo\data\images"

# Copy normal photos: 80 train, 20 validation, 15 test
$normales = Get-ChildItem "$src\normales" -Filter "*.jpeg" | Sort-Object Name
$i = 0
foreach ($f in $normales) {
    if ($i -lt 80)      { Copy-Item $f.FullName "$dst\train\" }
    elseif ($i -lt 100) { Copy-Item $f.FullName "$dst\validation\" }
    else                { Copy-Item $f.FullName "$dst\test\" }
    $i++
}
Write-Host "Normales: $i fotos procesadas"

# Copy shadow photos: 30 train, 7 validation, 7 test
$sombra = Get-ChildItem "$src\sombraluz tenue" -Filter "*.jpeg" | Sort-Object Name
$i = 0
foreach ($f in $sombra) {
    if ($i -lt 30)      { Copy-Item $f.FullName "$dst\train\" }
    elseif ($i -lt 37)  { Copy-Item $f.FullName "$dst\validation\" }
    else                { Copy-Item $f.FullName "$dst\test\" }
    $i++
}
Write-Host "Sombra: $i fotos procesadas"

# Copy tilted photos: 30 train, 3 validation, 10 test
$inclin = Get-ChildItem "$src\ligera inclinación ángulo" -Filter "*.jpeg" | Sort-Object Name
$i = 0
foreach ($f in $inclin) {
    if ($i -lt 30)      { Copy-Item $f.FullName "$dst\train\" }
    elseif ($i -lt 33)  { Copy-Item $f.FullName "$dst\validation\" }
    else                { Copy-Item $f.FullName "$dst\test\" }
    $i++
}
Write-Host "Inclinacion: $i fotos procesadas"

Write-Host ""
Write-Host "=== RESULTADO FINAL ==="
Write-Host "train:     " (Get-ChildItem "$dst\train").Count
Write-Host "validation:" (Get-ChildItem "$dst\validation").Count
Write-Host "test:      " (Get-ChildItem "$dst\test").Count
