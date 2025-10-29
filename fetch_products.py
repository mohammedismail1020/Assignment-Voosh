import requests
import json
import time
import sqlite3
import logging
from datetime import datetime
from requests.exceptions import RequestException, Timeout, HTTPError

# NEW: Setup Logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('pipeline.log'),  # Main log file
        logging.StreamHandler()  # Console
    ]
)
error_logger = logging.getLogger('errors')
error_handler = logging.FileHandler('error.log')
error_handler.setLevel(logging.ERROR)
error_logger.addHandler(error_handler)

def fetch_products(max_retries=3, timeout=10):
    """
    Fetches raw products with error handling and logging.
    """
    logger = logging.getLogger('fetch')
    url = "https://fakestoreapi.com/products"
    products = []
    
    for attempt in range(max_retries):
        try:
            logger.info(f"Fetching (attempt {attempt + 1}/{max_retries})...")
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            
            data = response.json()
            if not isinstance(data, list):
                raise ValueError("Bad response format")
            
            for product in data:
                cleaned = {
                    'id': product.get('id', None),
                    'title': product.get('title', 'Unknown'),
                    'price': product.get('price', 0.0),
                    'description': product.get('description', ''),
                    'category': product.get('category', 'Unknown'),
                    'image': product.get('image', ''),
                    'rating': product.get('rating', {'rate': 0.0, 'count': 0})
                }
                if cleaned['id'] is None or cleaned['title'] == 'Unknown':
                    logger.warning(f"Skipping invalid product: {product}")
                    continue
                products.append(cleaned)
            
            logger.info(f"Raw fetch: {len(products)} products.")
            return products
            
        except Timeout:
            logger.warning(f"Timeout—retrying...")
        except HTTPError as e:
            logger.error(f"HTTP error: {e}—retrying...")
        except RequestException as e:
            logger.error(f"Request failed: {e}—retrying...")
        except (ValueError, KeyError) as e:
            logger.error(f"Parse error: {e}")
            raise  # Re-raise to fail the pipeline
        
        if attempt < max_retries - 1:
            wait = 2 ** attempt
            logger.info(f"Wait {wait}s...")
            time.sleep(wait)
        else:
            logger.error("All retries failed.")
            raise RequestException("Fetch failed after all retries")
    
    return products

def transform_products(products, usd_to_inr=83):
    """
    Transforms data with logging.
    """
    logger = logging.getLogger('transform')
    transformed = []
    for product in products:
        trans = {
            'product_id': product['id'],
            'name': product['title'],
            'price_usd': product['price'],
            'desc': product['description'][:100] + '...' if len(product['description']) > 100 else product['description'],
            'category_norm': product['category'].lower().replace("men's", "mens").replace("women's", "womens"),
            'image_url': product['image'],
            'avg_rating': product['rating']['rate'],
            'review_count': product['rating']['count']
        }
        
        if trans['price_usd'] < 50 or trans['avg_rating'] < 3.0:
            logger.info(f"Filtering out: {trans['name']} (price: ${trans['price_usd']}, rating: {trans['avg_rating']})")
            continue
        
        trans['price_inr'] = round(trans['price_usd'] * usd_to_inr, 2)
        trans['is_expensive'] = trans['price_usd'] > 100
        trans['total_value_inr'] = round(trans['price_inr'] * (1 + trans['avg_rating'] / 10), 2)
        
        transformed.append(trans)
    
    logger.info(f"Transformed: {len(transformed)} products (from {len(products)} raw).")
    if not transformed:
        raise ValueError("No products after transformation")
    return transformed

def store_to_db(transformed_products, db_file='products.db'):
    """
    Stores to SQLite with logging; creates logs table.
    """
    logger = logging.getLogger('store')
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        
        # Create logs table if not exists
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS logs (
                run_id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                status TEXT NOT NULL,
                message TEXT
            )
        ''')
        
        # Existing products table creation...
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS products (
                product_id INTEGER PRIMARY KEY,
                name TEXT NOT NULL,
                price_usd REAL NOT NULL,
                desc TEXT,
                category_norm TEXT,
                image_url TEXT,
                avg_rating REAL,
                review_count INTEGER,
                price_inr REAL,
                is_expensive BOOLEAN,
                total_value_inr REAL
            )
        ''')
        
        for product in transformed_products:
            cursor.execute('''
                INSERT OR REPLACE INTO products 
                (product_id, name, price_usd, desc, category_norm, image_url, avg_rating, review_count, 
                 price_inr, is_expensive, total_value_inr)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                product['product_id'], product['name'], product['price_usd'], product['desc'],
                product['category_norm'], product['image_url'], product['avg_rating'], product['review_count'],
                product['price_inr'], product['is_expensive'], product['total_value_inr']
            ))
        
        conn.commit()
        cursor.execute('SELECT COUNT(*) FROM products')
        count = cursor.fetchone()[0]
        logger.info(f"Stored/Updated {len(transformed_products)} products in {db_file}. Total records: {count}")
        
        # Sample preview
        cursor.execute('SELECT name, price_usd, price_inr FROM products LIMIT 3')
        for row in cursor.fetchall():
            logger.info(f"Sample: {row[0]}: ${row[1]} USD / ₹{row[2]} INR")
        
    except sqlite3.Error as e:
        logger.error(f"DB Error: {e}")
        raise
    finally:
        conn.close()

def log_run_status(status, message, db_file='products.db'):
    """
    NEW: Log run to DB (tracks last successful time).
    """
    timestamp = datetime.now().isoformat()
    try:
        conn = sqlite3.connect(db_file)
        cursor = conn.cursor()
        cursor.execute(
            'INSERT INTO logs (timestamp, status, message) VALUES (?, ?, ?)',
            (timestamp, status, message)
        )
        conn.commit()
        conn.close()
        logging.info(f"Run logged: {status} - {message}")
    except sqlite3.Error as e:
        logging.error(f"Failed to log run: {e}")

# BONUS: Optional Email Alert on Failure (uncomment & configure)
# import smtplib
# from email.mime.text import MimeText
# def send_alert_email(error_msg, sender_email='your@gmail.com', app_password='your_app_pass', recipient='you@gmail.com'):
#     msg = MimeText(f"ETL Pipeline Failed: {error_msg}\nTime: {datetime.now()}")
#     msg['Subject'] = 'ETL Alert: Pipeline Failed'
#     msg['From'] = sender_email
#     msg['To'] = recipient
#     with smtplib.SMTP_SSL('smtp.gmail.com', 465) as server:
#         server.login(sender_email, app_password)
#         server.sendmail(sender_email, recipient, msg.as_string())

# Main: Fetch → Transform → Store with Monitoring
if __name__ == "__main__":
    run_start = datetime.now().isoformat()
    status = "FAILED"
    message = ""
    try:
        logging.info("Pipeline started.")
        raw_products = fetch_products()
        if raw_products:
            transformed_products = transform_products(raw_products)
            if transformed_products:
                store_to_db(transformed_products)
                status = "SUCCESS"
                message = f"Fetched {len(raw_products)}, transformed {len(transformed_products)}, stored OK. Last success: {run_start}"
            else:
                message = "Transformation failed: No products left."
        else:
            message = "Fetch failed: No raw products."
        
        print(f"\nPipeline Status: {status}")
        log_run_status(status, message)
        
        # BONUS: Email on failure (uncomment)
        # if status == "FAILED":
        #     send_alert_email(message)
            
    except Exception as e:
        error_msg = f"Pipeline crashed: {str(e)}"
        logging.error(error_msg)
        error_logger.error(error_msg)
        print(f"\nPipeline Status: FAILED - {error_msg}")
        log_run_status(status, error_msg)
        
        # BONUS: Email
        # send_alert_email(error_msg)
        
        raise  # Optional: Re-raise for CI/CD