# ai_manager.py - النظام الذكي المتعدد المصادر (كامل الخدمات)
# الإصدار: 5.1 (Smart Multi-Source AI - Complete) - معدل لـ Railway
import os
import logging
import asyncio
import google.generativeai as genai
from openai import OpenAI as OpenAIClient
import aiohttp
import re
import json
import base64
from datetime import datetime, timedelta
from enum import Enum
from typing import Optional, List, Dict, Any, Tuple, Union
from dataclasses import dataclass, field
from urllib.parse import urlparse
import hashlib
from collections import OrderedDict
import time

logger = logging.getLogger(__name__)

class ServiceType(Enum):
    """أنواع الخدمات المتاحة"""
    CHAT = "chat"
    IMAGE = "image"
    VIDEO = "video"

class Provider(Enum):
    """مزودي الخدمات"""
    GOOGLE = "google"
    OPENAI = "openai"
    STABILITY = "stability"
    LUMA = "luma"
    KLING = "kling"

@dataclass
class ModelInfo:
    """معلومات الموديل"""
    name: str
    provider: Provider
    service_type: ServiceType
    version: str = "1.0"
    release_date: Optional[str] = None
    max_tokens: int = 2048
    is_latest: bool = False
    is_deprecated: bool = False
    priority: int = 100
    supports_enhancement: bool = True

@dataclass
class ProviderConfig:
    """إعدادات مزود الخدمة"""
    name: Provider
    api_key: Optional[str] = None
    enabled: bool = False
    daily_limit: int = 100
    usage_today: int = 0
    errors_today: int = 0
    avg_response_time: float = 0.0
    last_error: Optional[str] = None
    
    # قائمة الموديلات المكتشفة
    discovered_models: Dict[ServiceType, List[ModelInfo]] = field(default_factory=dict)
    
    # الموديل النشط الحالي
    active_models: Dict[ServiceType, str] = field(default_factory=dict)

class SmartAIManager:
    """
    مدير ذكاء اصطناعي ذكي يكتشف الموديلات تلقائياً
    ويرتبها من الأحدث إلى الأقدم مع دعم كامل للخدمات
    """
    
    def __init__(self, db):
        """تهيئة المدير الذكي"""
        self.db = db
        self.user_limits_cache = OrderedDict()
        self.max_cache_size = 1000
        
        # تخزين جلسات الدردشة مع وقت انتهاء
        self.chat_sessions: Dict[int, Dict[str, Any]] = {}
        self.session_timeout = timedelta(hours=1)
        
        # ذاكرة مؤقتة للصور والفيديوهات المولدة
        self.generated_files_cache: Dict[str, Dict] = {}
        
        # تهيئة جميع المزودين
        self.providers: Dict[Provider, ProviderConfig] = self._init_providers()
        
        # علامة للاكتشاف
        self.discovery_completed = False
        self.discovery_lock = asyncio.Lock()
        
        # إعدادات الـ timeout الافتراضية
        self.default_timeout = aiohttp.ClientTimeout(total=30)
        
        logger.info("🚀 تم تهيئة النظام الذكي للذكاء الاصطناعي (كامل الخدمات)")
    
    def _init_providers(self) -> Dict[Provider, ProviderConfig]:
        """تهيئة إعدادات جميع المزودين"""
        providers = {
            Provider.GOOGLE: ProviderConfig(
                name=Provider.GOOGLE,
                api_key=os.getenv("GOOGLE_AI_API_KEY"),
                daily_limit=int(os.getenv("GOOGLE_DAILY_LIMIT", "50"))  # تقليل القيمة الافتراضية
            ),
            Provider.OPENAI: ProviderConfig(
                name=Provider.OPENAI,
                api_key=os.getenv("OPENAI_API_KEY"),
                daily_limit=int(os.getenv("OPENAI_DAILY_LIMIT", "30"))
            ),
            Provider.STABILITY: ProviderConfig(
                name=Provider.STABILITY,
                api_key=os.getenv("STABILITY_API_KEY"),
                daily_limit=int(os.getenv("STABILITY_DAILY_LIMIT", "20"))
            ),
            Provider.LUMA: ProviderConfig(
                name=Provider.LUMA,
                api_key=os.getenv("LUMAAI_API_KEY"),
                daily_limit=int(os.getenv("LUMA_DAILY_LIMIT", "10"))
            ),
            Provider.KLING: ProviderConfig(
                name=Provider.KLING,
                api_key=os.getenv("KLING_API_KEY"),
                daily_limit=int(os.getenv("KLING_DAILY_LIMIT", "5"))
            )
        }
        
        # التحقق من صحة API Keys
        for provider_name, config in providers.items():
            if not config.api_key or config.api_key.strip() == "":
                config.enabled = False
                logger.warning(f"⚠️ {provider_name.value}: مفتاح API غير موجود أو فارغ")
            elif len(config.api_key) < 10:
                config.enabled = False
                logger.warning(f"⚠️ {provider_name.value}: مفتاح API غير صالح (قصير جداً)")
        
        return providers
    
    async def ensure_discovery(self):
        """التأكد من أن الاكتشاف تم"""
        if not self.discovery_completed:
            async with self.discovery_lock:
                if not self.discovery_completed:
                    await self._setup_and_discover_async()
                    self.discovery_completed = True
    
    async def _setup_and_discover_async(self):
        """إعداد APIs واكتشاف الموديلات بشكل غير متزامن"""
        try:
            logger.info("🔍 بدء اكتشاف الموديلات تلقائياً...")
            
            # 1. إعداد Google API واكتشاف موديلاته
            await self._setup_and_discover_google()
            
            # 2. إعداد OpenAI API واكتشاف موديلاته
            await self._setup_and_discover_openai()
            
            # 3. إعداد باقي APIs
            await self._setup_other_apis()
            
            # 4. تسجيل النتائج
            self._log_discovery_results()
            
            # 5. اختيار أفضل موديل لكل خدمة
            self._select_best_models()
            
            logger.info("✅ اكتمل اكتشاف وتنظيم الموديلات")
            
        except Exception as e:
            logger.error(f"❌ فشل اكتشاف الموديلات: {e}", exc_info=True)
    
    async def _setup_and_discover_google(self):
        """إعداد Google API واكتشاف موديلاته"""
        google_config = self.providers[Provider.GOOGLE]
        
        if not google_config.api_key:
            logger.warning("⚠️ Google API Key غير موجود")
            return
        
        try:
            # التحقق من صحة المفتاح
            if not google_config.api_key.startswith("AI"):
                logger.warning("⚠️ Google API Key لا يبدو بصيغة صحيحة")
            
            # إعداد API
            genai.configure(api_key=google_config.api_key)
            google_config.enabled = True
            
            # اكتشاف جميع الموديلات المتاحة
            logger.info("🔍 جاري اكتشاف موديلات Google...")
            all_models = []
            
            try:
                models_list = genai.list_models()
                all_models = [m.name.replace('models/', '') for m in models_list]
                logger.info(f"📊 وجد {len(all_models)} موديل Google")
            except Exception as e:
                logger.warning(f"⚠️ فشل جلب قائمة الموديلات: {e}")
                # قائمة احتياطية (مع الموزة أولاً)
                all_models = [
                    'nano-banana-pro-preview',  # 1
                    'imagen-4.0-generate-preview-06-06',  # 2
                    'imagen-3.0-generate-001',  # 3
                    'gemini-2.5-flash', 'gemini-2.5-pro', 'gemini-3-flash-preview',
                    'gemini-3-pro-preview', 'gemini-2.0-flash',
                    'veo-3.0-generate-001'
                ]
            
            # تصنيف الموديلات
            google_config.discovered_models = {
                ServiceType.CHAT: [],
                ServiceType.IMAGE: [],
                ServiceType.VIDEO: []
            }
            
            for model_name in all_models:
                model_info = self._analyze_google_model(model_name)
                if model_info:
                    google_config.discovered_models[model_info.service_type].append(model_info)
                # ترتيب الموديلات (الأولوية للأقل رقم priority)
            for service_type in google_config.discovered_models:
                google_config.discovered_models[service_type].sort(
                    key=lambda x: x.priority, # ترتيب تصاعدي (10 ثم 20 ثم 50...)
                    reverse=False 
                )
                
            # طباعة الموديل المختار للتأكد
            if google_config.discovered_models[ServiceType.CHAT]:
                top_model = google_config.discovered_models[ServiceType.CHAT][0]
                logger.info(f"👑 تم اختيار موديل القمة: {top_model.name} (Priority: {top_model.priority})")
                google_config.active_models[ServiceType.CHAT] = top_model.name
            
        except Exception as e:
            logger.error(f"❌ فشل إعداد Google: {e}", exc_info=True)
            google_config.enabled = False

    def _analyze_google_model(self, model_name: str) -> Optional[ModelInfo]:
        """تحليل موديل Google (يدعم صيغ الكتابة المختلفة . و -)"""
        try:
            model_lower = model_name.lower()
            
            # السماح بجميع الموديلات
            
            # تصنيف الخدمة
            if 'gemini' in model_lower and 'tts' not in model_lower:
                service_type = ServiceType.CHAT
            elif 'imagen' in model_lower or 'banana' in model_lower:
                service_type = ServiceType.IMAGE
            elif 'veo' in model_lower:
                service_type = ServiceType.VIDEO
            else:
                return None
            
            # ====================================================
            # ⚡️ نظام الأولويات (مع دعم النقطة والشرطة) ⚡️
            # ====================================================
            version = "1.0"
            priority = 100 
            
            if service_type == ServiceType.CHAT:
                # 1. Gemini 3.0 (يلتقط 3.0 و 3-0 و 3 فقط)
                if 'gemini-3' in model_lower:
                    version = "3.0"
                    priority = 10 
                
                # 2. Gemini 2.5 (يلتقط 2.5 و 2-5)
                elif 'gemini-2.5' in model_lower or 'gemini-2-5' in model_lower:
                    version = "2.5"
                    priority = 15
                
                # 3. Gemini 2.0 (يلتقط 2.0 و 2-0)
                elif 'gemini-2.0' in model_lower or 'gemini-2-0' in model_lower:
                    version = "2.0"
                    priority = 20
                
                # 4. Gemini 1.5 (يلتقط 1.5 و 1-5)
                elif 'gemini-1.5' in model_lower or 'gemini-1-5' in model_lower:
                    version = "1.5"
                    priority = 30
                
                # 5. Gemini 1.0
                elif 'gemini-1.0' in model_lower or 'gemini-1-0' in model_lower or 'gemini-pro' in model_lower:
                    version = "1.0"
                    priority = 40
                
            elif service_type == ServiceType.IMAGE:
                # ترتيب الصور
                if 'banana' in model_lower:      priority = 5
                elif 'imagen-4' in model_lower:  priority = 10
                elif 'imagen-3' in model_lower:  priority = 20
                elif 'imagen-2' in model_lower:  priority = 30
                else: priority = 50
                
            elif service_type == ServiceType.VIDEO:
                if 'veo' in model_lower: priority = 10
            
            return ModelInfo(
                name=model_name, provider=Provider.GOOGLE, service_type=service_type, 
                version=version, is_latest=('latest' in model_lower), priority=priority
            )
            
        except: return None
    
    async def _setup_and_discover_openai(self):
        """إعداد OpenAI API واكتشاف موديلاته"""
        openai_config = self.providers[Provider.OPENAI]
        
        if not openai_config.api_key:
            logger.warning("⚠️ OpenAI API Key غير موجود")
            return
        
        try:
            # التحقق من صحة المفتاح
            if not openai_config.api_key.startswith("sk-"):
                logger.warning("⚠️ OpenAI API Key لا يبدو بصيغة صحيحة (يجب أن يبدأ بـ sk-)")
            
            self.openai_client = OpenAIClient(api_key=openai_config.api_key)
            openai_config.enabled = True
            
            logger.info("🔍 جاري اكتشاف موديلات OpenAI...")
            
            openai_config.discovered_models = {
                ServiceType.CHAT: [],
                ServiceType.IMAGE: [],
                ServiceType.VIDEO: []
            }
            
            # قائمة الموديلات المعروفة
            known_openai_models = {
                ServiceType.CHAT: [
                    'gpt-4o', 'gpt-4o-mini', 'gpt-4-turbo', 'gpt-4', 
                    'gpt-3.5-turbo', 'gpt-3.5-turbo-instruct'
                ],
                ServiceType.IMAGE: [
                    'dall-e-3', 'dall-e-2'
                ]
            }
            
            # اختبار كل موديل
            for service_type, models in known_openai_models.items():
                for model_name in models:
                    model_info = self._analyze_openai_model(model_name, service_type)
                    if model_info:
                        openai_config.discovered_models[service_type].append(model_info)
            
            # ترتيب الموديلات
            for service_type in openai_config.discovered_models:
                openai_config.discovered_models[service_type].sort(key=lambda x: x.priority)
            
        except Exception as e:
            logger.error(f"❌ فشل إعداد OpenAI: {e}", exc_info=True)
            openai_config.enabled = False
    
    def _analyze_openai_model(self, model_name: str, service_type: ServiceType) -> Optional[ModelInfo]:
        """تحليل موديل OpenAI"""
        try:
            model_lower = model_name.lower()
            version = "1.0"
            priority = 100
            
            if service_type == ServiceType.CHAT:
                if 'gpt-4o' in model_lower:
                    version = "4.0"
                    priority = 5 if 'mini' in model_lower else 10
                elif 'gpt-4-turbo' in model_lower:
                    version = "4.0"
                    priority = 15
                elif 'gpt-4' in model_lower:
                    version = "4.0"
                    priority = 20
                elif 'gpt-3.5-turbo' in model_lower:
                    version = "3.5"
                    priority = 30 if 'instruct' in model_lower else 25
                else:
                    return None
                    
            elif service_type == ServiceType.IMAGE:
                if 'dall-e-3' in model_lower:
                    version = "3.0"
                    priority = 5
                elif 'dall-e-2' in model_lower:
                    version = "2.0"
                    priority = 10
                else:
                    return None
            
            return ModelInfo(
                name=model_name,
                provider=Provider.OPENAI,
                service_type=service_type,
                version=version,
                priority=priority,
                supports_enhancement=True
            )
            
        except Exception as e:
            logger.debug(f"⚠️ فشل تحليل موديل OpenAI {model_name}: {e}")
            return None
    
    async def _setup_other_apis(self):
        """إعداد باقي APIs"""
        # Stability AI
        stability_config = self.providers[Provider.STABILITY]
        if stability_config.api_key:
            # التحقق من صحة المفتاح
            if len(stability_config.api_key) > 20:
                stability_config.enabled = True
                self.stability_headers = {
                    "Authorization": f"Bearer {stability_config.api_key}",
                    "Content-Type": "application/json",
                    "Accept": "application/json",
                    "User-Agent": "SmartAIManager/5.1"
                }
                self.stability_url = os.getenv(
                    "STABLE_DIFFUSION_URL", 
                    "https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image"
                )
        
        # Luma AI
        luma_config = self.providers[Provider.LUMA]
        if luma_config.api_key:
            if len(luma_config.api_key) > 20:
                luma_config.enabled = True
                self.luma_headers = {
                    "Authorization": f"Bearer {luma_config.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "SmartAIManager/5.1"
                }
        
        # Kling AI
        kling_config = self.providers[Provider.KLING]
        if kling_config.api_key:
            if len(kling_config.api_key) > 20:
                kling_config.enabled = True
                self.kling_headers = {
                    "Authorization": f"Bearer {kling_config.api_key}",
                    "Content-Type": "application/json",
                    "User-Agent": "SmartAIManager/5.1"
                }
    
    def _log_discovery_results(self):
        """تسجيل نتائج الاكتشاف (عرض القائمة كاملة)"""
        logger.info("=" * 50)
        logger.info("📊 نتائج اكتشاف الموديلات (القائمة الكاملة):")
        
        for provider_name, config in self.providers.items():
            if not config.enabled:
                continue
            
            logger.info(f"\n🔹 {provider_name.value.upper()}:")
            
            for service_type, models in config.discovered_models.items():
                if models:
                    logger.info(f"  {service_type.value} ({len(models)} models):")
                    for i, model in enumerate(models):
                        # ✅ تعديل: وضع نجمة لأول 16 موديل (لأننا سنحاول 16 مرة)
                        status = "⭐" if i < 16 else "  "
                        logger.info(f"    {status} [{i+1}] {model.name} (Priority: {model.priority})")
                else:
                    logger.info(f"  {service_type.value}: ❌ لا توجد موديلات")
        
        logger.info("=" * 50)
    
    def _select_best_models(self):
        """اختيار أفضل موديل لكل خدمة"""
        for provider_name, config in self.providers.items():
            if not config.enabled:
                continue
            
            for service_type, models in config.discovered_models.items():
                if models:
                    best_model = min(models, key=lambda x: x.priority)
                    config.active_models[service_type] = best_model.name
    
    def _extract_version_number(self, version_str: str) -> float:
        """استخراج رقم الإصدار"""
        try:
            return float(version_str)
        except:
            return 1.0
    
    # ==================== دوال النظام الذكي ====================
    
    def get_available_providers(self, service_type: ServiceType) -> List[ProviderConfig]:
        """الحصول على المزودين المتاحين"""
        available = []
        
        for provider in self.providers.values():
            if not provider.enabled or provider.usage_today >= provider.daily_limit:
                continue
            
            if service_type == ServiceType.CHAT:
                if provider.name in [Provider.GOOGLE, Provider.OPENAI]:
                    available.append(provider)
            elif service_type == ServiceType.IMAGE:
                if provider.name in [Provider.GOOGLE, Provider.OPENAI, Provider.STABILITY]:
                    available.append(provider)
            elif service_type == ServiceType.VIDEO:
                if provider.name in [Provider.GOOGLE, Provider.LUMA, Provider.KLING]:
                    available.append(provider)
        
        available.sort(key=lambda x: (x.errors_today, x.usage_today))
        return available
    
    def get_active_model(self, provider: Provider, service_type: ServiceType) -> Optional[str]:
        """الحصول على الموديل النشط"""
        config = self.providers.get(provider)
        if not config or not config.enabled:
            return None
        
        return config.active_models.get(service_type)
    
    def rotate_model(self, provider: Provider, service_type: ServiceType, current_model: str = None) -> Optional[str]:
        """تدوير الموديل إلى التالي"""
        config = self.providers.get(provider)
        if not config or service_type not in config.discovered_models:
            return None
        
        models = config.discovered_models[service_type]
        if not models:
            return None
        
        if not current_model or current_model not in [m.name for m in models]:
            new_model = models[0].name
        else:
            current_index = None
            for i, model in enumerate(models):
                if model.name == current_model:
                    current_index = i
                    break
            
            if current_index is None or current_index >= len(models) - 1:
                new_model = models[0].name
            else:
                new_model = models[current_index + 1].name
        
        config.active_models[service_type] = new_model
        logger.info(f"🔄 تدوير موديل {provider.value}/{service_type.value}: {current_model or 'None'} → {new_model}")
        return new_model
    
    async def _execute_with_fallback(self, provider: Provider, service_type: ServiceType, 
                                   execute_func, max_retries: int = 3):
        """تنفيذ مع نظام fallback"""
        config = self.providers.get(provider)
        if not config or not config.enabled:
            raise Exception(f"المزود {provider.value} غير مفعل")
        
        current_model = self.get_active_model(provider, service_type)
        original_model = current_model
        
        for attempt in range(max_retries):
            try:
                if not current_model:
                    models = config.discovered_models.get(service_type, [])
                    if not models:
                        raise Exception(f"لا توجد موديلات لـ {service_type.value}")
                    current_model = models[0].name
                    config.active_models[service_type] = current_model
                
                logger.info(f"🔄 محاولة {attempt+1}/{max_retries} مع {provider.value}/{current_model}")
                
                result = await execute_func(current_model)
                return result
                
            except Exception as e:
                error_msg = str(e)
                logger.error(f"❌ خطأ في {provider.value}/{current_model}: {error_msg}")
                
                is_quota_error = any(keyword in error_msg.lower() for keyword in [
                    '429', 'quota', 'rate limit', 'resource exhausted'
                ])
                is_model_error = any(keyword in error_msg.lower() for keyword in [
                    '404', 'not found', 'invalid model', 'model not found'
                ])
                
                if is_quota_error or is_model_error:
                    logger.warning(f"⚠️ {provider.value}: خطأ في الموديل {current_model}")
                    
                    next_model = self.rotate_model(provider, service_type, current_model)
                    
                    if next_model and next_model != current_model:
                        current_model = next_model
                        logger.info(f"🔄 الانتقال للموديل التالي: {next_model}")
                        continue
                    else:
                        logger.error(f"❌ لا توجد موديلات بديلة لـ {provider.value}")
                        break
                else:
                    logger.error(f"❌ {provider.value}: خطأ غير متعلق بالموديل")
                    break
        
        raise Exception(f"فشلت جميع محاولات {provider.value} ({max_retries} محاولات)")
    
    # ==================== خدمة المحادثة (كاملة) ====================
    
    async def chat_with_ai(self, user_id: int, message: str) -> str:
        """خدمة المحادثة مع fallback ذكي"""
        try:
            # التأكد من أن الاكتشاف تم
            await self.ensure_discovery()
            
            # التحقق من صحة المدخلات
            if not isinstance(user_id, int) or user_id <= 0:
                return "❌ معرف مستخدم غير صالح."
            
            if not message or len(message.strip()) < 1:
                return "❌ الرسالة فارغة أو قصيرة جداً."
            
            if len(message) > 4000:
                message = message[:4000] + "..."
            
            allowed, remaining = self.check_user_limit(user_id, "ai_chat")
            if not allowed:
                return f"❌ عذراً، لقد استهلكت رصيدك اليومي من الرسائل. ({remaining} متبقي)"
            
            providers = self.get_available_providers(ServiceType.CHAT)
            
            if not providers:
                return "⚠️ جميع خدمات المحادثة غير متاحة حالياً."
            
            errors = []
            
            for provider_config in providers:
                try:
                    provider = provider_config.name
                    
                    async def execute_chat(model_name: str):
                        if provider == Provider.GOOGLE:
                            return await self._chat_with_google(model_name, user_id, message)
                        elif provider == Provider.OPENAI:
                            return await self._chat_with_openai(model_name, message)
                        else:
                            raise Exception(f"مزود غير مدعوم: {provider}")
                    
                    # ✅ زيادة المحاولات إلى 16 (كما طلبت)
                    response = await self._execute_with_fallback(
                        provider, ServiceType.CHAT, execute_chat, max_retries=16
                    )
                    
                    if response:
                        self.update_user_usage(user_id, "ai_chat")
                        provider_config.usage_today += 1
                        self.db.save_ai_conversation(user_id, "chat", message, response)
                        return response
                        
                except Exception as e:
                    error_msg = str(e)
                    errors.append(f"{provider_config.name.value}: {error_msg[:100]}")
                    provider_config.errors_today += 1
                    provider_config.last_error = error_msg
                    continue
            
            if errors:
                error_summary = "\n".join(errors[:3])
                return f"⚠️ جميع خدمات المحادثة فشلت:\n{error_summary}"
            return "⚠️ حدث خطأ غير متوقع."
            
        except Exception as e:
            logger.error(f"❌ خطأ عام في المحادثة: {e}", exc_info=True)
            return "⚠️ حدث خطأ غير متوقع في النظام."
    
    async def _chat_with_google(self, model_name: str, user_id: int, message: str) -> str:
        """الدردشة مع Google Gemini"""
        try:
            # تنظيف الجلسات القديمة
            self._cleanup_old_sessions()
            
            model = genai.GenerativeModel(model_name)
            
            if user_id not in self.chat_sessions:
                chat = model.start_chat(history=[
                    {"role": "user", "parts": ["أنت مساعد ذكي بالعربية. رد باختصار ووضوح."]},
                    {"role": "model", "parts": ["حسناً، أنا جاهز للمساعدة."]}
                ])
                self.chat_sessions[user_id] = {
                    "chat": chat,
                    "last_activity": datetime.now()
                }
            
            session = self.chat_sessions[user_id]
            session["last_activity"] = datetime.now()
            chat_session = session["chat"]
            
            response = await asyncio.wait_for(
                chat_session.send_message_async(message),
                timeout=30.0
            )
            
            if response and response.text:
                return self._clean_response(response.text)
            else:
                raise Exception("رد فارغ من Google")
                
        except asyncio.TimeoutError:
            raise Exception("انتهى وقت الانتظار للرد من Google")
        except Exception as e:
            raise Exception(f"Google Gemini error: {str(e)}")
    
    async def _chat_with_openai(self, model_name: str, message: str) -> str:
        """الدردشة مع OpenAI"""
        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.openai_client.chat.completions.create(
                        model=model_name,
                        messages=[{"role": "user", "content": message}],
                        max_tokens=1000,
                        temperature=0.7
                    )
                ),
                timeout=30.0
            )
            return response.choices[0].message.content
        except asyncio.TimeoutError:
            raise Exception("انتهى وقت الانتظار للرد من OpenAI")
        except Exception as e:
            raise Exception(f"OpenAI error: {str(e)}")
    
    def _cleanup_old_sessions(self):
        """تنظيف الجلسات القديمة"""
        now = datetime.now()
        to_delete = []
        
        for user_id, session_data in self.chat_sessions.items():
            if now - session_data["last_activity"] > self.session_timeout:
                to_delete.append(user_id)
        
        for user_id in to_delete:
            del self.chat_sessions[user_id]
        
        if to_delete:
            logger.info(f"🧹 تم تنظيف {len(to_delete)} جلسة قديمة")
    
    # ==================== خدمة الصور (كاملة) ====================
    
    async def generate_image(self, user_id: int, prompt: str, style: str = "realistic") -> Tuple[Optional[str], str]:
        """توليد صور مع fallback ذكي"""
        try:
            # التأكد من أن الاكتشاف تم
            await self.ensure_discovery()
            
            # التحقق من صحة المدخلات
            if not isinstance(user_id, int) or user_id <= 0:
                return None, "❌ معرف مستخدم غير صالح."
            
            if not prompt or len(prompt.strip()) < 3:
                return None, "❌ الوصف قصير جداً (أقل من 3 أحرف)."
            
            if len(prompt) > 2000:
                prompt = prompt[:2000]
            
            allowed, remaining = self.check_user_limit(user_id, "image_gen")
            if not allowed:
                return None, f"❌ انتهى رصيد الصور اليومي. ({remaining} متبقي)"
            
            providers = self.get_available_providers(ServiceType.IMAGE)
            
            if not providers:
                return None, "⚠️ جميع خدمات توليد الصور غير متاحة."
            
            errors = []
            
            # تحسين الوصف
            enhanced_prompt = await self._enhance_image_prompt(prompt, style)
            
            for provider_config in providers:
                try:
                    provider = provider_config.name
                    
                    async def execute_image(model_name: str):
                        if provider == Provider.GOOGLE:
                            return await self._generate_image_google(model_name, enhanced_prompt)
                        elif provider == Provider.OPENAI:
                            return await self._generate_image_openai(model_name, enhanced_prompt)
                        elif provider == Provider.STABILITY:
                            return await self._generate_image_stability(enhanced_prompt, style)
                        else:
                            raise Exception(f"مزود غير مدعوم للصور: {provider}")
                    
                    # ✅ زيادة المحاولات إلى 6
                    image_url = await self._execute_with_fallback(
                        provider, ServiceType.IMAGE, execute_image, max_retries=6
                    )
                    
                    if image_url:
                        self.update_user_usage(user_id, "image_gen")
                        provider_config.usage_today += 1
                        self.db.save_generated_file(user_id, "image", prompt, image_url)
                        
                        # حفظ في الكاش
                        cache_key = f"image_{user_id}_{hashlib.md5(prompt.encode()).hexdigest()[:12]}"
                        self.generated_files_cache[cache_key] = {
                            "url": image_url,
                            "prompt": prompt,
                            "provider": provider.value,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        return image_url, "✅ تم إنشاء الصورة بنجاح"
                        
                except Exception as e:
                    error_msg = str(e)
                    errors.append(f"{provider_config.name.value}: {error_msg[:100]}")
                    provider_config.errors_today += 1
                    provider_config.last_error = error_msg
                    continue
            
            if errors:
                error_summary = "\n".join(errors[:3])
                return None, f"❌ جميع خدمات الصور فشلت:\n{error_summary}"
            return None, "❌ حدث خطأ غير متوقع."
            
        except Exception as e:
            logger.error(f"❌ خطأ عام في توليد الصور: {e}", exc_info=True)
            return None, "⚠️ حدث خطأ غير متوقع في خدمة الصور."
    
    async def _enhance_image_prompt(self, prompt: str, style: str) -> str:
        """تحسين وصف الصورة"""
        style_map = {
            "realistic": "فوتوغرافي واقعي، تفاصيل دقيقة، إضاءة طبيعية",
            "anime": "أنمي ياباني، ألوان زاهية، عيون كبيرة",
            "fantasy": "فانتازيا سحرية، كائنات خيالية، إضاءة دراماتيكية",
            "cyberpunk": "مستقبلي، نيون، تكنولوجيا متقدمة",
            "watercolor": "ألوان مائية، فرشاة فنية، انسيابية"
        }
        
        style_desc = style_map.get(style, "فوتوغرافي واقعي")
        
        enhancement_prompt = f"""
        حول هذا الوصف لصورة احترافية باللغة الإنجليزية:
        الوصف: {prompt}
        النمط: {style} ({style_desc})
        
        المتطلبات:
        1. وصف مفصل باللغة الإنجليزية
        2. التركيز على الإضاءة والتركيب
        3. إضافة تفاصيل فنية
        4. مناسب لتوليد صور AI
        
        الإخراج: وصف إنجليزي فقط
        """
        
        try:
            # استخدام Google Gemini لتحسين الوصف
            google_config = self.providers[Provider.GOOGLE]
            if google_config.enabled and google_config.active_models.get(ServiceType.CHAT):
                model_name = google_config.active_models[ServiceType.CHAT]
                model = genai.GenerativeModel(model_name)
                response = await asyncio.wait_for(
                    model.generate_content_async(enhancement_prompt),
                    timeout=15.0
                )
                if response and response.text:
                    enhanced = response.text.strip()
                    if len(enhanced) > 50:  # التأكد من وجود محتوى كافي
                        return enhanced
        except Exception as e:
            logger.debug(f"⚠️ فشل تحسين الوصف: {e}")
        
        return f"{prompt}, {style} style, professional photography, detailed, 4k"
    
    async def _generate_image_google(self, model_name: str, prompt: str) -> str:
        """توليد صورة (يدعم التبديل التلقائي عند الفشل)"""
        try:
            logger.info(f"🎨 محاولة توليد صورة باستخدام: {model_name}...")
            
            if not os.path.exists("downloads"):
                os.makedirs("downloads")
            filename = f"downloads/img_{int(time.time())}.png"

            api_key = self.providers[Provider.GOOGLE].api_key
            # استخدام الموديل المتغير (الذي يحدده نظام الـ Fallback)
            url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:predict?key={api_key}"
            
            payload = {
                "instances": [{"prompt": prompt}],
                "parameters": {"sampleCount": 1, "aspectRatio": "1:1"}
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers={'Content-Type': 'application/json'}) as response:
                    # إذا فشل الموديل (مثلاً 404 للموزة)، نرفع خطأ ليتم التقاطه
                    if response.status != 200:
                        error_text = await response.text()
                        # نرفع Exception يحتوي على 404 ليفهم النظام ويجرب الموديل التالي
                        raise Exception(f"Google Error {response.status}: {error_text}")
                    
                    result = await response.json()
                    
                    predictions = result.get('predictions', [])
                    if not predictions:
                        raise Exception("لم يتم استلام تنبؤات (Empty Response)")
                    
                    b64_data = predictions[0].get('bytesBase64Encoded')
                    if not b64_data:
                         b64_data = predictions[0].get('image', {}).get('bytesBase64Encoded')
                         
                    if not b64_data:
                        raise Exception("تنسيق الصورة غير معروف")
                        
                    image_data = base64.b64decode(b64_data)
                    with open(filename, "wb") as f:
                        f.write(image_data)
                        
                    return filename

        except Exception as e:
            # هنا لا نقوم بالتحويل لـ OpenAI فوراً
            # بل نترك الخطأ يصعد لكي يقوم _execute_with_fallback بتجربة موديل جوجل التالي
            raise e
    
    async def _generate_image_openai(self, model_name: str, prompt: str) -> str:
        """توليد صورة باستخدام OpenAI DALL-E"""
        try:
            response = await asyncio.wait_for(
                asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.openai_client.images.generate(
                        model=model_name,
                        prompt=prompt[:1000],
                        size="1024x1024",
                        quality="standard",
                        n=1
                    )
                ),
                timeout=60.0
            )
            return response.data[0].url
        except asyncio.TimeoutError:
            raise Exception("انتهى وقت الانتظار لـ DALL-E")
        except Exception as e:
            raise Exception(f"DALL-E error: {str(e)}")
    
    async def _generate_image_stability(self, prompt: str, style: str) -> str:
        """توليد صورة باستخدام Stability AI"""
        try:
            style_presets = {
                "realistic": "photographic",
                "anime": "anime",
                "fantasy": "fantasy-art",
                "cyberpunk": "neon-punk",
                "watercolor": None  # لا يوجد preset
            }
            
            data = {
                "text_prompts": [{"text": prompt, "weight": 1}],
                "cfg_scale": 7,
                "height": 1024,
                "width": 1024,
                "samples": 1,
                "steps": 30,
            }
            
            style_preset = style_presets.get(style)
            if style_preset:
                data["style_preset"] = style_preset
            
            async with aiohttp.ClientSession(timeout=self.default_timeout) as session:
                async with session.post(
                    self.stability_url,
                    headers=self.stability_headers,
                    json=data
                ) as response:
                    if response.status == 200:
                        result = await response.json()
                        
                        # Stability تعيد base64
                        if "artifacts" in result and len(result["artifacts"]) > 0:
                            image_data = result["artifacts"][0]["base64"]
                            
                            # هنا يمكنك:
                            # 1. حفظ الصورة في ملف مؤقت
                            # 2. رفعها لخدمة تخزين
                            # 3. إعادة رابطها
                            
                            # مؤقتاً نعيد رابط وهمي مع تنبيف
                            logger.warning("⚠️ Stability AI: تم استلام الصورة كـ base64، تحتاج معالجة")
                            return f"data:image/png;base64,{image_data}"
                        else:
                            raise Exception("لا توجد صور في استجابة Stability")
                    else:
                        error_text = await response.text()[:200]
                        raise Exception(f"Stability API error: {response.status} - {error_text}")
        except aiohttp.ClientError as e:
            raise Exception(f"Stability AI connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Stability AI error: {str(e)}")
    
    # ==================== خدمة الفيديو (كاملة) ====================
    
    async def generate_video(self, user_id: int, prompt: str, image_url: str = None) -> Tuple[Optional[str], str]:
        """توليد فيديو مع fallback ذكي"""
        try:
            # التأكد من أن الاكتشاف تم
            await self.ensure_discovery()
            
            # التحقق من صحة المدخلات
            if not isinstance(user_id, int) or user_id <= 0:
                return None, "❌ معرف مستخدم غير صالح."
            
            if not prompt or len(prompt.strip()) < 5:
                return None, "❌ الوصف قصير جداً (أقل من 5 أحرف)."
            
            if len(prompt) > 1000:
                prompt = prompt[:1000]
            
            allowed, remaining = self.check_user_limit(user_id, "video_gen")
            if not allowed:
                return None, f"❌ انتهى رصيد الفيديوهات اليومي. ({remaining} متبقي)"
            
            providers = self.get_available_providers(ServiceType.VIDEO)
            
            if not providers:
                return None, "⚠️ جميع خدمات توليد الفيديو غير متاحة."
            
            errors = []
            
            # تحسين الوصف
            enhanced_prompt = await self._enhance_video_prompt(prompt)
            
            for provider_config in providers:
                try:
                    provider = provider_config.name
                    
                    async def execute_video(model_name: str):
                        if provider == Provider.GOOGLE:
                            return await self._generate_video_google(model_name, enhanced_prompt, image_url)
                        elif provider == Provider.LUMA:
                            return await self._generate_video_luma(enhanced_prompt, image_url)
                        elif provider == Provider.KLING:
                            return await self._generate_video_kling(enhanced_prompt, image_url)
                        else:
                            raise Exception(f"مزود غير مدعوم للفيديو: {provider}")
                    
                    # ✅ زيادة المحاولات إلى 6
                    video_url = await self._execute_with_fallback(
                        provider, ServiceType.VIDEO, execute_video, max_retries=6
                    )
                    
                    if video_url:
                        self.update_user_usage(user_id, "video_gen")
                        provider_config.usage_today += 1
                        self.db.save_generated_file(user_id, "video", prompt, video_url)
                        
                        # حفظ في الكاش
                        cache_key = f"video_{user_id}_{hashlib.md5(prompt.encode()).hexdigest()[:12]}"
                        self.generated_files_cache[cache_key] = {
                            "url": video_url,
                            "prompt": prompt,
                            "provider": provider.value,
                            "timestamp": datetime.now().isoformat()
                        }
                        
                        return video_url, "✅ تم إنشاء الفيديو بنجاح"
                        
                except Exception as e:
                    error_msg = str(e)
                    errors.append(f"{provider_config.name.value}: {error_msg[:100]}")
                    provider_config.errors_today += 1
                    provider_config.last_error = error_msg
                    continue
            
            if errors:
                error_summary = "\n".join(errors[:3])
                return None, f"❌ جميع خدمات الفيديو فشلت:\n{error_summary}"
            return None, "❌ حدث خطأ غير متوقع."
            
        except Exception as e:
            logger.error(f"❌ خطأ عام في توليد الفيديو: {e}", exc_info=True)
            return None, "⚠️ حدث خطأ غير متوقع في خدمة الفيديو."
    
    async def _enhance_video_prompt(self, prompt: str) -> str:
        """تحسين وصف الفيديو"""
        enhancement_prompt = f"""
        حول هذا الوصف لفيديو احترافي باللغة الإنجليزية:
        الوصف: {prompt}
        
        المتطلبات:
        1. فيديو 5 ثواني
        2. وصف سينمائي باللغة الإنجليزية
        3. تحديد حركة الكاميرا (zoom, pan, tilt)
        4. وصف الحركة داخل المشهد
        5. الإضاءة والمزاج
        6. مناسب لتوليد فيديو AI
        
        الإخراج: وصف إنجليزي فقط
        """
        
        try:
            google_config = self.providers[Provider.GOOGLE]
            if google_config.enabled and google_config.active_models.get(ServiceType.CHAT):
                model_name = google_config.active_models[ServiceType.CHAT]
                model = genai.GenerativeModel(model_name)
                response = await asyncio.wait_for(
                    model.generate_content_async(enhancement_prompt),
                    timeout=15.0
                )
                if response and response.text:
                    enhanced = response.text.strip()
                    if len(enhanced) > 100:  # التأكد من وجود محتوى كافي
                        return enhanced
        except Exception as e:
            logger.debug(f"⚠️ فشل تحسين وصف الفيديو: {e}")
        
        return f"{prompt}, cinematic, 5 seconds, smooth camera movement, professional lighting"
    
    async def _generate_video_google(self, model_name: str, prompt: str, image_url: str = None) -> str:
        """توليد فيديو باستخدام Google Veo"""
        # TODO: تنفيذ API call لـ Google Veo
        # مؤقتاً نستخدم fallback لـ Luma إذا كان متاح
        luma_config = self.providers[Provider.LUMA]
        if luma_config.enabled:
            return await self._generate_video_luma(prompt, image_url)
        raise Exception("Google Veo غير متوفر حالياً")
    
    async def _generate_video_luma(self, prompt: str, image_url: str = None) -> str:
        """توليد فيديو باستخدام Luma AI"""
        try:
            url = "https://api.lumalabs.ai/dream-machine/v1/generations"
            payload = {
                "prompt": prompt,
                "aspect_ratio": "16:9"
            }
            
            if image_url:
                url = "https://api.lumalabs.ai/dream-machine/v1/generations/image"
                payload["image_url"] = image_url
            
            timeout = aiohttp.ClientTimeout(total=300)  # 5 دقائق للفيديو
            
            async with aiohttp.ClientSession(timeout=timeout) as session:
                # بدء التوليد
                async with session.post(url, headers=self.luma_headers, json=payload) as response:
                    if response.status in [200, 201]:
                        data = await response.json()
                        generation_id = data.get("id")
                        
                        if not generation_id:
                            raise Exception("لم يتم استلام معرف التوليد")
                        
                        # الانتظار والتحقق (بحد أقصى 10 محاولات)
                        for attempt in range(10):
                            await asyncio.sleep(10)  # 10 ثواني بين المحاولات
                            
                            async with session.get(
                                f"{url}/{generation_id}",
                                headers=self.luma_headers
                            ) as check_response:
                                if check_response.status == 200:
                                    status_data = await check_response.json()
                                    state = status_data.get("state")
                                    
                                    if state == "completed":
                                        video_url = status_data.get("assets", {}).get("video")
                                        if video_url:
                                            return video_url
                                    elif state == "failed":
                                        failure_reason = status_data.get('failure_reason', 'غير معروف')
                                        raise Exception(f"فشل التوليد: {failure_reason}")
                                    elif state == "processing":
                                        continue  # استمر في الانتظار
                        
                        raise Exception("انتهى وقت الانتظار للفيديو (100 ثانية)")
                    else:
                        error_text = await response.text()[:200]
                        raise Exception(f"Luma API error: {response.status} - {error_text}")
        except aiohttp.ClientError as e:
            raise Exception(f"Luma AI connection error: {str(e)}")
        except Exception as e:
            raise Exception(f"Luma AI error: {str(e)}")
    
    async def _generate_video_kling(self, prompt: str, image_url: str = None) -> str:
        """توليد فيديو باستخدام Kling AI"""
        # TODO: تنفيذ API call لـ Kling AI
        # مؤقتاً نستخدم fallback لـ Luma
        luma_config = self.providers[Provider.LUMA]
        if luma_config.enabled:
            return await self._generate_video_luma(prompt, image_url)
        raise Exception("Kling AI غير متوفر حالياً")
    
    # ==================== دوال مساعدة ====================
    
    def _clean_response(self, text: str) -> str:
        """تنظيف الردود"""
        if not text:
            return "عذراً، لم أستطع تكوين رد مناسب."
        
        try:
            clean_text = re.sub(r'THOUGHT:.*?(?=\n\n|\Z)', '', text, flags=re.DOTALL | re.IGNORECASE)
            clean_text = clean_text.replace("THOUGHT:", "").strip()
            
            if not clean_text or len(clean_text) < 2:
                return text
            return clean_text
        except:
            return text
    
    def check_user_limit(self, user_id: int, service_type: str) -> Tuple[bool, int]:
        """فحص حدود المستخدم"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            cache_key = f"{user_id}_{today}_{service_type}"
            
            # تحديث الكاش (LRU)
            if cache_key in self.user_limits_cache:
                current_usage = self.user_limits_cache[cache_key]
                # نقل المفتاح للنهاية (الأحدث)
                self.user_limits_cache.move_to_end(cache_key)
            else:
                with self.db.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute(
                        'SELECT usage_count FROM ai_usage WHERE user_id = ? AND service_type = ? AND usage_date = ?',
                        (user_id, service_type, today)
                    )
                    result = cursor.fetchone()
                    current_usage = result[0] if result else 0
                    self.user_limits_cache[cache_key] = current_usage
            
            # التحكم بحجم الكاش
            if len(self.user_limits_cache) > self.max_cache_size:
                self.user_limits_cache.popitem(last=False)
            
            limits_config = {
                "ai_chat": int(os.getenv("DAILY_AI_LIMIT", "20")),
                "image_gen": int(os.getenv("DAILY_IMAGE_LIMIT", "5")),
                "video_gen": int(os.getenv("DAILY_VIDEO_LIMIT", "2"))
            }
            
            limit = limits_config.get(service_type, 20)
            
            if current_usage >= limit:
                return False, 0
            
            return True, limit - current_usage
            
        except Exception as e:
            logger.error(f"❌ خطأ في فحص الحدود: {e}", exc_info=True)
            return True, 999
    
    def update_user_usage(self, user_id: int, service_type: str) -> bool:
        """تحديث استخدام المستخدم"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            cache_key = f"{user_id}_{today}_{service_type}"
            
            current = self.user_limits_cache.get(cache_key, 0)
            self.user_limits_cache[cache_key] = current + 1
            
            # تحديث قاعدة البيانات
            with self.db.get_connection() as conn:
                conn.execute('''
                INSERT INTO ai_usage (user_id, service_type, usage_date, usage_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, service_type, usage_date) 
                DO UPDATE SET usage_count = usage_count + 1
                ''', (user_id, service_type, today))
                conn.commit()
            return True
        except Exception as e:
            logger.error(f"❌ خطأ في تحديث الاستخدام: {e}", exc_info=True)
            return False
    
    def get_available_services(self) -> Dict[str, bool]:
        """الحصول على حالة الخدمات"""
        return {
            "chat": len(self.get_available_providers(ServiceType.CHAT)) > 0,
            "image_generation": len(self.get_available_providers(ServiceType.IMAGE)) > 0,
            "video_generation": len(self.get_available_providers(ServiceType.VIDEO)) > 0
        }
    
    def get_user_stats(self, user_id: int) -> Dict[str, int]:
        """إحصائيات المستخدم"""
        stats = {}
        today = datetime.now().strftime('%Y-%m-%d')
        
        for service_type in ["ai_chat", "image_gen", "video_gen"]:
            cache_key = f"{user_id}_{today}_{service_type}"
            stats[service_type] = self.user_limits_cache.get(cache_key, 0)
        
        return stats
    
    def get_system_stats(self) -> Dict[str, Any]:
        """إحصائيات النظام"""
        stats = {
            "providers": {},
            "total_requests_today": 0,
            "total_errors_today": 0,
            "discovery_completed": self.discovery_completed,
            "active_sessions": len(self.chat_sessions),
            "cache_size": len(self.user_limits_cache),
            "timestamp": datetime.now().isoformat()
        }
        
        for provider_name, config in self.providers.items():
            if config.enabled:
                stats["providers"][provider_name.value] = {
                    "enabled": True,
                    "usage_today": config.usage_today,
                    "errors_today": config.errors_today,
                    "daily_limit": config.daily_limit,
                    "remaining_limit": config.daily_limit - config.usage_today,
                    "last_error": config.last_error[:100] if config.last_error else None,
                    "active_models": config.active_models,
                    "discovered_models_count": {
                        st.value: len(models)
                        for st, models in config.discovered_models.items()
                    }
                }
                stats["total_requests_today"] += config.usage_today
                stats["total_errors_today"] += config.errors_today
        
        return stats
    
    def reset_daily_counts(self):
        """إعادة تعيين العدادات"""
        today = datetime.now().strftime('%Y-%m-%d')
        
        # إعادة تعيين كاش المستخدمين
        keys_to_delete = []
        for key in self.user_limits_cache.keys():
            if not key.endswith(today):
                keys_to_delete.append(key)
        
        for key in keys_to_delete:
            del self.user_limits_cache[key]
        
        # إعادة تعيين المزودين
        for provider in self.providers.values():
            provider.usage_today = 0
            provider.errors_today = 0
            provider.last_error = None
        
        logger.info("🔄 تم إعادة تعيين العدادات اليومية")

# استيراد للتوافق
AIManager = SmartAIManager