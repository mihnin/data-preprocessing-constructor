# Create project directory structure for data-preprocessing-constructor

# Define the root directory
$rootDir = "c:\data-preprocessing-constructor"

# Function to ensure a directory exists
function EnsureDirectory {
    param (
        [string]$path
    )
    
    if (-not (Test-Path -Path $path)) {
        New-Item -Path $path -ItemType Directory -Force | Out-Null
        Write-Host "Created directory: $path"
    } else {
        Write-Host "Directory already exists: $path" -ForegroundColor DarkGray
    }
}

# Function to ensure a file exists
function EnsureFile {
    param (
        [string]$path
    )
    
    if (-not (Test-Path -Path $path)) {
        New-Item -Path $path -ItemType File -Force | Out-Null
        Write-Host "Created file: $path"
    } else {
        Write-Host "File already exists: $path" -ForegroundColor DarkGray
    }
}

# Create frontend structure
EnsureDirectory -path "$rootDir\frontend"
EnsureDirectory -path "$rootDir\frontend\src"
EnsureDirectory -path "$rootDir\frontend\src\assets"
EnsureDirectory -path "$rootDir\frontend\src\components"
EnsureDirectory -path "$rootDir\frontend\src\router"
EnsureDirectory -path "$rootDir\frontend\src\services"
EnsureDirectory -path "$rootDir\frontend\src\store"
EnsureDirectory -path "$rootDir\frontend\src\views"

# Create frontend files
EnsureFile -path "$rootDir\frontend\package.json"
EnsureFile -path "$rootDir\frontend\src\App.vue"
EnsureFile -path "$rootDir\frontend\src\main.js"
EnsureFile -path "$rootDir\frontend\src\components\Header.vue"
EnsureFile -path "$rootDir\frontend\src\router\index.js"
EnsureFile -path "$rootDir\frontend\src\services\api.js"
EnsureFile -path "$rootDir\frontend\src\services\datasetService.js"
EnsureFile -path "$rootDir\frontend\src\services\preprocessingService.js"
EnsureFile -path "$rootDir\frontend\src\store\index.js"
EnsureFile -path "$rootDir\frontend\src\views\DataUploadView.vue"
EnsureFile -path "$rootDir\frontend\src\views\HomeView.vue"
EnsureFile -path "$rootDir\frontend\src\views\PreprocessingView.vue"
EnsureFile -path "$rootDir\frontend\src\views\PreviewExportView.vue"
EnsureFile -path "$rootDir\frontend\vue.config.js"

# Create backend structure
EnsureDirectory -path "$rootDir\backend"
EnsureDirectory -path "$rootDir\backend\controllers"
EnsureDirectory -path "$rootDir\backend\services"
EnsureDirectory -path "$rootDir\backend\utils"

# Create backend files
EnsureFile -path "$rootDir\backend\main.py"
EnsureFile -path "$rootDir\backend\requirements.txt"
EnsureFile -path "$rootDir\backend\controllers\__init__.py"
EnsureFile -path "$rootDir\backend\controllers\datasets.py"
EnsureFile -path "$rootDir\backend\controllers\preprocessing.py"
EnsureFile -path "$rootDir\backend\services\__init__.py"
EnsureFile -path "$rootDir\backend\services\dataset_service.py"
EnsureFile -path "$rootDir\backend\services\preprocessing_service.py"
EnsureFile -path "$rootDir\backend\utils\__init__.py"
EnsureFile -path "$rootDir\backend\utils\analysis_utils.py"
EnsureFile -path "$rootDir\backend\utils\file_utils.py"

# Create data structure
EnsureDirectory -path "$rootDir\data"
EnsureDirectory -path "$rootDir\data\uploads"
EnsureDirectory -path "$rootDir\data\processed"
EnsureDirectory -path "$rootDir\data\temp"

# Create root files
EnsureFile -path "$rootDir\Dockerfile"
EnsureFile -path "$rootDir\docker-compose.yml"
EnsureFile -path "$rootDir\nginx.conf"
EnsureFile -path "$rootDir\README.md"

Write-Host "`nProject structure creation complete!" -ForegroundColor Green

