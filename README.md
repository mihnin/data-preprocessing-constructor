# Data Preprocessing Builder

[Русская версия](README.ru.md)

## Description
The Data Preprocessing Builder is a web application designed to automate the data preparation pipeline before building predictive models. The application supports both tabular data and time series, providing an intuitive interface for various transformation methods.

## Key Features
- **Upload and Analyze**: Supports CSV and Excel file formats for data upload and analysis.
- **Auto-Recommendations**: Automatically detects data types and recommends suitable preprocessing methods.
- **Live Preview**: Visualize and preview the results of data transformations in real-time.
- **Export Data**: Export the processed dataset for use in other tools and models.
- **Parameter Management**: Save and re-apply scaling parameters for consistent transformations.

## Supported Preprocessing Methods

### General Methods
- **Missing Value Imputation**: Fill missing values using mean, median, mode, or drop rows.
- **Outlier Detection**: Handle outliers using Z-score or Interquartile Range (IQR) methods.
- **Data Scaling**: Standardize numeric data with StandardScaler or MinMaxScaler.
- **Categorical Encoding**: Convert categorical variables using One-Hot or Label Encoding.
- **Dimensionality Reduction**: Apply Principal Component Analysis (PCA) to reduce the number of features.

### Time Series Methods
- **Lag Features**: Create lagged versions of variables for time series forecasting.
- **Rolling Statistics**: Calculate rolling window statistics (mean, std, min, max).
- **Date Component Extraction**: Extract features like year, month, quarter, and day of the week.
- **Inverse Scaling**: Revert scaled data back to its original values for interpretation.

## Running the Application with Docker

### Prerequisites
- Docker Desktop (for Windows or macOS) or Docker Engine (for Linux) installed.
- `docker-compose` installed (usually included with Docker Desktop).

### Instructions
1.  **Clone the repository:**
    ```bash
    git clone https://github.com/mihnin/data-preprocessing-constructor.git
    cd data-preprocessing-constructor
    ```

2.  **Run the application:**
    ```bash
    docker-compose up -d
    ```
    *Note for Linux users: You may need to run this command with `sudo`.*

3.  **Access the application:**
    Open your web browser and navigate to [http://localhost:8080](http://localhost:8080).

## Technology Stack
- **Frontend**: Vue.js 3, Element Plus
- **Backend**: Python 3.11, FastAPI
- **Libraries**: pandas, numpy, scikit-learn, statsmodels
- **Infrastructure**: Docker, Nginx

## Use Cases
- Preparing data for machine learning models.
- Preprocessing time series data for forecasting.
- Standardizing and normalizing datasets.
- Handling categorical variables and missing values.
- Identifying and removing outliers.