import os

# Elasticsearch Configuration
ELASTICSEARCH_CONFIG = {
	'host': os.getenv('ELASTICSEARCH_HOST', 'localhost'),
	'port': int(os.getenv('ELASTICSEARCH_PORT', '9200')),
	'username': None,  # Güvenlik aktifse doldur
	'password': None,  # Güvenlik aktifse doldur
	'use_ssl': False,
	'verify_certs': False
}

# User/tenant configuration (çoklu kullanıcı desteği)
USER_CONFIG = {
	'user_id': 'default_user',   # Her kullanıcı için benzersiz bir kimlik atayın
	'device_id': None            # Boş bırakılırsa cihaz adı otomatik alınır
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

# Model Configuration
MODEL_CONFIG = {
    'default_model': 'microsoft/DialoGPT-small',  # Start with smallest causal LM
    'available_models': [
        {
            'id': 'dialogpt-small',
            'name': 'microsoft/DialoGPT-small',
            'display_name': 'DialoGPT Small (Hafif)',
            'description': 'Küçük konuşma modeli, düşük bellek kullanımı',
            'size': '117M',
            'language_support': ['en'],
            'recommended_for': ['low_memory', 'basic_conversation']
        },
        {
            'id': 'gpt2-small',
            'name': 'gpt2',
            'display_name': 'GPT-2 Small (Ultra Hafif)',
            'description': 'En küçük GPT-2 modeli, minimal bellek kullanımı',
            'size': '124M',
            'language_support': ['en'],
            'recommended_for': ['ultra_low_memory', 'text_generation']
        },
        {
            'id': 'qwen2.5-3b',
            'name': 'Qwen/Qwen2.5-3B-Instruct',
            'display_name': 'Qwen 2.5 3B (Hızlı)',
            'description': 'Hızlı ve verimli, temel sorular için ideal',
            'size': '3B',
            'language_support': ['tr', 'en'],
            'recommended_for': ['basic_queries', 'fast_response']
        }
    ],
    'model_settings': {
        'max_new_tokens': 256,
        'temperature': 0.7,
        'top_p': 0.9,
        'repetition_penalty': 1.1,
        'no_repeat_ngram_size': 2,
        'max_generation_time': 30.0
    },
    'auto_fallback': True,  # Otomatik olarak daha küçük modele geç
    'fallback_order': ['gpt2-small', 'dialogpt-small', 'qwen2.5-3b']
}
