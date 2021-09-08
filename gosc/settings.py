"""
Django settings for gosc project.

Generated by 'django-admin startproject' using Django 2.2.13.

For more information on this file, see
https://docs.djangoproject.com/en/2.2/topics/settings/

For the full list of settings and their values, see
https://docs.djangoproject.com/en/2.2/ref/settings/
"""

# import os
#
# # Build paths inside the project like this: os.path.join(BASE_DIR, ...)
# BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
from datetime import timedelta
from pathlib import Path
import os
BASE_DIR = Path(__file__).resolve(strict=True).parent.parent

# Quick-start development settings - unsuitable for production
# See https://docs.djangoproject.com/en/2.2/howto/deployment/checklist/


# SECURITY WARNING: don't run with debug turned on in production!
DEBUG = True

ALLOWED_HOSTS = ['*']
INTERNAL_IPS = []

# Application definition

INSTALLED_APPS = [
    'django.contrib.admin',
    'django.contrib.auth',
    'django.contrib.contenttypes',
    'django.contrib.sessions',
    'django.contrib.messages',
    'django.contrib.staticfiles',

    'rest_framework',
    # 'rest_framework.authtoken',
    'drf_yasg',
    # 'tinymce',
    'corsheaders',

    'users',
    'servers',
    'api',
    'vpn',
    'service',
    'vo',
    'activity',
    'storage',
    'monitor',
    'docs',
]

MIDDLEWARE = [
    'django.middleware.security.SecurityMiddleware',
    'django.contrib.sessions.middleware.SessionMiddleware',
    'django.middleware.locale.LocaleMiddleware',
    'corsheaders.middleware.CorsMiddleware',
    'django.middleware.common.CommonMiddleware',
    'django.middleware.csrf.CsrfViewMiddleware',
    'django.contrib.auth.middleware.AuthenticationMiddleware',
    'django.contrib.messages.middleware.MessageMiddleware',
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
]

ROOT_URLCONF = 'gosc.urls'

TEMPLATES = [
    {
        'BACKEND': 'django.template.backends.django.DjangoTemplates',
        'DIRS': [Path('/').joinpath(BASE_DIR, 'templates'), ],
        'APP_DIRS': True,
        'OPTIONS': {
            'context_processors': [
                'django.template.context_processors.debug',
                'django.template.context_processors.request',
                'django.contrib.auth.context_processors.auth',
                'django.contrib.messages.context_processors.messages',
            ],
        },
    },
]

WSGI_APPLICATION = 'gosc.wsgi.application'

# CACHE
CACHES = {
    'default': {
        'BACKEND': 'django.core.cache.backends.locmem.LocMemCache',
    }
}

# Database
# https://docs.djangoproject.com/en/2.2/ref/settings/#databases
# 在文件security.py中配置


# Password validation
# https://docs.djangoproject.com/en/2.2/ref/settings/#auth-password-validators

AUTH_PASSWORD_VALIDATORS = [
    {
        'NAME': 'django.contrib.auth.password_validation.UserAttributeSimilarityValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.MinimumLengthValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.CommonPasswordValidator',
    },
    {
        'NAME': 'django.contrib.auth.password_validation.NumericPasswordValidator',
    },
]


# Internationalization
# https://docs.djangoproject.com/en/2.2/topics/i18n/

LANGUAGE_CODE = 'zh-hans'

TIME_ZONE = 'UTC'

USE_I18N = True

USE_L10N = True

USE_TZ = True

LANGUAGES = [
    ('zh-hans', 'Simplified Chinese'),
    ('en', 'English')
]
# 翻译文件所在目录
LOCALE_PATHS = (
    os.path.join(BASE_DIR, 'locale'),
)

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/2.2/howto/static-files/

STATIC_URL = '/static/'
STATIC_ROOT = Path('/').joinpath(BASE_DIR, 'collect_static')
# 静态文件查找路径
STATICFILES_DIRS = [
    Path('/').joinpath(BASE_DIR, 'static'),
]

MEDIA_ROOT = Path('/').joinpath(BASE_DIR, 'media')

# session 有效期设置
SESSION_SAVE_EVERY_REQUEST = True
SESSION_EXPIRE_AT_BROWSER_CLOSE = True  # True：关闭浏览器，则Cookie失效。
# SESSION_COOKIE_AGE=60*30   #30分钟

# 自定义用户模型
AUTH_USER_MODEL = 'users.UserProfile'

# 避免django把未以/结尾的url重定向到以/结尾的url
# APPEND_SLASH=False

# 登陆url
LOGIN_URL = '/accounts/login/'
LOGOUT_URL = '/accounts/logout/'
LOGIN_REDIRECT_URL = '/'    # 默认重定向url
LOGOUT_REDIRECT_URL = '/'

# 第三方应用登录认证
THIRD_PARTY_APP_AUTH = {
    # 科技云通行证
    'SCIENCE_CLOUD': {
        # 'client_id': 000,
        # 'client_secret': 'xxx',
        'client_home_url': 'https://vms.cstcloud.cn',
        'client_callback_url': 'https://vms.cstcloud.cn/accounts/callback/',  # 认证回调地址
        # 'login_url': 'https://passport.escience.cn/oauth2/authorize?response_type=code&theme=simple',
        'login_url': 'https://passport.escience.cn/oauth2/authorize?response_type=code&theme=embed',
        'token_url': 'https://passport.escience.cn/oauth2/token',
        'logout_url': 'https://passport.escience.cn/logout'
    },
}


REST_FRAMEWORK = {
    'PAGE_SIZE': 100,
    'DEFAULT_PAGINATION_CLASS': 'rest_framework.pagination.PageNumberPagination',
    'DEFAULT_AUTHENTICATION_CLASSES': (
        'core.jwt.authentication.CreateUserJWTAuthentication',
        'rest_framework.authentication.BasicAuthentication',
        'rest_framework.authentication.SessionAuthentication'
    ),
    'EXCEPTION_HANDLER': 'api.viewsets.exception_handler',
}

# TinyMCE
# TINYMCE_DEFAULT_CONFIG = {
#     "theme": "silver",
#     "height": 500,
#     "menubar": True,
#     "plugins": "advlist,autolink,lists,link,image imagetools,charmap,print,preview,anchor,"
#                "searchreplace,visualblocks,code,fullscreen,insertdatetime,media,table,paste,"
#                "code,help,wordcount",
#     "toolbar": "undo redo | formatselect | bold italic backcolor | alignleft aligncenter "
#                "alignright alignjustify | bullist numlist outdent indent | removeformat | preview fullscreen | help",
#     'file_picker_callback': 'file_picker_callback'
# }
# TINYMCE_COMPRESSOR = True
# TINYMCE_FILEBROWSER = True

LOGGING_FILES_DIR = '/var/log/gosc'
if not os.path.exists(LOGGING_FILES_DIR):
    os.makedirs(LOGGING_FILES_DIR, exist_ok=True)

LOGGING = {
    'version': 1,
    'disable_existing_loggers': False,
    'formatters': {
        'verbose': {
            'format': '%(levelname)s %(asctime)s %(module)s %(process)d %(thread)d %(message)s'
        },
        'simple': {
            'format': '%(levelname)s %(message)s'
        },
        'dubug_formatter': {
            'format': '%(levelname)s %(asctime)s %(message)s'
        },
    },
    'filters': {
        'require_debug_false': {
            '()': 'django.utils.log.RequireDebugFalse',
        },
        'require_debug_true': {
            '()': 'django.utils.log.RequireDebugTrue',
        },
    },
    'handlers': {
        # # logging file settings
        'file': {
            'level': 'WARNING',
            'class': 'concurrent_log_handler.ConcurrentRotatingFileHandler',
            'filename': os.path.join(LOGGING_FILES_DIR, 'vms.log'),
            'formatter': 'verbose',
            'maxBytes': 1024*1024*200,  # 200MB
            'backupCount': 10           # 最多10个文件
        },
        # output to console settings
        'console': {
            'level': 'DEBUG',
            'filters': ['require_debug_true'],  # working with debug mode
            'class': 'logging.StreamHandler',
            'formatter': 'simple'
        }
    },
    'loggers': {
        # 'django.db.backends': {
        #     'handlers': ['console'],
        #     'propagate': True,
        #     'level': 'DEBUG',
        # },
        'django.request': {
            'handlers': ['file', 'console'],
            'level': 'ERROR',
            'propagate': False,
        },
    },
}

SIMPLE_JWT = {
    'ALGORITHM': 'RS512',
    # 'SIGNING_KEY': '',
    # 'VERIFYING_KEY': None,
    # 'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    # 'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('JWT',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'username',
    'USER_ID_CLAIM': 'username',
    'TOKEN_TYPE_CLAIM': 'token_type',

    'JTI_CLAIM': 'jti'
}

PASSPORT_JWT = {
    'ALGORITHM': 'RS512',
    'SIGNING_KEY': '',
    # 'VERIFYING_KEY': None,
    'ACCESS_TOKEN_LIFETIME': timedelta(minutes=5),
    'REFRESH_TOKEN_LIFETIME': timedelta(days=1),
    'AUDIENCE': None,
    'ISSUER': None,

    'AUTH_HEADER_TYPES': ('Bearer',),
    'AUTH_HEADER_NAME': 'HTTP_AUTHORIZATION',
    'USER_ID_FIELD': 'username',
    'USER_ID_CLAIM': 'cstnetId',
    'TOKEN_TYPE_CLAIM': 'type',
    'EXPIRATION_CLAIM': 'exp',

    # 'JTI_CLAIM': 'jti'
}


# drf-yasg
SWAGGER_SETTINGS = {
    # 'LOGIN_URL': reverse_lazy('admin:login'),
    # 'LOGOUT_URL': '/admin/logout',
    'USE_SESSION_AUTH': True,
    'PERSIST_AUTH': True,
    'REFETCH_SCHEMA_WITH_AUTH': True,
    'REFETCH_SCHEMA_ON_LOGOUT': True,

    'SECURITY_DEFINITIONS': {
        'Basic': {
            'type': 'basic'
        },
        'Bearer': {
            'in': 'header',
            'name': 'Authorization',
            'type': 'apiKey',
        }
    },
}


# 跨域
# CORS_ALLOWED_ORIGINS = [
#     "https://example.com",
# ]

CORS_ALLOW_ALL_ORIGINS = True       # 允许所有请求来源跨域


# 安全配置导入
from .security import *


if DEBUG:
    from .test_settings import TEST_CASE

    # django debug toolbar
    INSTALLED_APPS.append('debug_toolbar')
    MIDDLEWARE.append('debug_toolbar.middleware.DebugToolbarMiddleware')
    DEBUG_TOOLBAR_CONFIG = {
        # 'SHOW_COLLAPSED': True,
    }
    INTERNAL_IPS += ['127.0.0.1']     # 通过这些IP地址访问时，页面才会出现django debug toolbar面板
