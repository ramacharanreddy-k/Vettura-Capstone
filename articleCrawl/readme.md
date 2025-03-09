# Article Crawling Pipeline

This repository contains a comprehensive pipeline for crawling, processing, and managing articles from a website. The pipeline is designed to extract articles from categories and subcategories, organize the content into a structured directory hierarchy, and ensure data integrity through logging and safe deletion of incomplete data.

## Prerequisites

Before running the scripts, ensure you have the following installed:

- Python 3.x
- Selenium
- ChromeDriver (automatically managed by `webdriver_manager`)
- Required Python packages (install via `pip install -r requirements.txt`)

You can install the required packages using:

```bash
pip install selenium webdriver-manager requests logging datetime time
```

## Scripts Overview

### 1. **`categoryManager.py`**

This script manages the processing of categories and subcategories. It uses Selenium to navigate the website and extract content, then organizes it into a structured directory hierarchy.

#### Key Features:
- **Category Processing**: Processes categories and subcategories, creating directories and saving metadata.
- **Headless Browser**: Runs Chrome in headless mode for efficient scraping.
- **Logging**: Logs all actions and errors for debugging and monitoring.

#### Usage:

```bash
python categoryManager.py
```

#### Output:
- A structured directory hierarchy containing categories, subcategories, and articles.

### 2. **`contentProcessor.py`**

This script processes the content of articles, including text, images, tables, and PDFs. It downloads and organizes the content into appropriate directories.

#### Key Features:
- **Content Extraction**: Extracts text, images, tables, and PDFs from articles.
- **Directory Management**: Creates directories for each article and organizes content.
- **Metadata Management**: Saves metadata for each article and subcategory.

#### Usage:

```bash
python contentProcessor.py
```

#### Output:
- A structured directory hierarchy containing article content, images, tables, and metadata.

### 3. **`htmlScrapper.py`**

This script is responsible for scraping HTML content from articles. It extracts text, images, tables, and other relevant content.

#### Key Features:
- **HTML Scraping**: Extracts content from HTML using specific selectors.
- **Image Downloading**: Downloads images and saves them locally.
- **Content Organization**: Organizes extracted content into a structured format.

#### Usage:

```bash
python htmlScrapper.py
```

#### Output:
- Extracted content from articles, including text, images, tables, and metadata.

### 4. **`logger.py`**

This script sets up a logging system for the entire pipeline. It logs all actions, errors, and debugging information to both the console and a log file.

#### Key Features:
- **Logging Configuration**: Configures logging for both file and console output.
- **Timestamped Logs**: Generates log files with timestamps for easy tracking.
- **Debugging Support**: Provides detailed logging for debugging purposes.

#### Usage:

```bash
python logger.py
```

#### Output:
- Log files in the `logs/` directory containing detailed logging information.

### 5. **`main.py`**

This is the main script that orchestrates the entire pipeline. It loads configuration, ensures directories exist, and processes all categories and subcategories.

#### Key Features:
- **Configuration Management**: Loads configuration from a JSON file.
- **Directory Management**: Ensures required directories exist.
- **Pipeline Orchestration**: Coordinates the processing of categories and subcategories.

#### Usage:

```bash
python main.py
```

#### Output:
- A fully processed directory hierarchy containing all scraped content.

### 6. **`safeDelete.py`**

This script checks for incomplete articles and deletes them if necessary. It ensures that only complete articles are retained in the directory hierarchy.

#### Key Features:
- **Incomplete Article Detection**: Checks for missing `content.json` files.
- **Safe Deletion**: Deletes incomplete articles in a controlled manner.
- **Dry Run Mode**: Allows for testing without actually deleting anything.

#### Usage:

```bash
python safeDelete.py
```

#### Output:
- A cleaned directory hierarchy with only complete articles retained.

### 7. **`utils.py`**

This script provides utility functions for the pipeline, including filename sanitization, configuration loading, and directory management.

#### Key Features:
- **Filename Sanitization**: Converts strings to valid filenames.
- **Configuration Loading**: Loads configuration from a JSON file.
- **Directory Management**: Ensures directories exist and are properly structured.

#### Usage:

```bash
python utils.py
```

#### Output:
- Utility functions that support the rest of the pipeline.

## Running the Pipeline

1. **Ensure Directories Exist**:
   ```bash
   python main.py
   ```

2. **Process Categories and Subcategories**:
   ```bash
   python categoryManager.py
   ```

3. **Process Article Content**:
   ```bash
   python contentProcessor.py
   ```

4. **Scrape HTML Content**:
   ```bash
   python htmlScrapper.py
   ```

5. **Check for Incomplete Articles**:
   ```bash
   python safeDelete.py
   ```

## Logging

All scripts generate log files in the `logs/` directory. These logs are useful for debugging and tracking the progress of the scraping process.

## Customization

- **Target Website**: Modify the configuration in `config/config.json` to scrape a different website.
- **Selectors**: Adjust the CSS selectors in the scripts if the website structure changes.
- **Output Paths**: Change the output file paths in the scripts if needed.

## Troubleshooting

- **WebDriver Issues**: Ensure that ChromeDriver is correctly installed and matches your Chrome browser version.
- **Dynamic Content**: If the website uses heavy JavaScript, you may need to adjust the waiting times in the scripts.
- **Logs**: Check the log files for detailed error messages and debugging information.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.

---

This README provides an overview of the scripts and how to use them. For more detailed information, refer to the comments and documentation within each script.