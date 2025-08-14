# Elasticsearch Configuration
ELASTICSEARCH_CONFIG = {
    'host': 'localhost',
    'port': 9200,
    'username': None,  # Güvenlik aktifse doldur
    'password': None,  # Güvenlik aktifse doldur
    'use_ssl': False,
    'verify_certs': False
}

# Index Names
INDICES = {
    'web_info': 'web-info',
    'system_info': 'system-info'
}

# Monitoring Configuration
MONITORING_CONFIG = {
    'default_interval': 300,  # 5 dakika
    'max_retries': 3,
    'retry_delay': 60  # 1 dakika
}

# Web Info Configuration
WEB_CONFIG = {
    'expected_country': 'TR',
    'timeout': 30,
    'max_speed_test_attempts': 3
}