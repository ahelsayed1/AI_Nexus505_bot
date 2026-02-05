# database.py - النسخة النهائية مع دعم الذكاء الاصطناعي
import sqlite3
import logging
from datetime import datetime, timedelta
import os

logger = logging.getLogger(__name__)

class Database:
    def __init__(self, db_name="bot_database.db"):
        """تهيئة قاعدة البيانات"""
        self.db_name = db_name
        self.init_database()
    
    def get_connection(self):
        """الحصول على اتصال بقاعدة البيانات"""
        conn = sqlite3.connect(self.db_name)
        conn.row_factory = sqlite3.Row
        return conn
    
    def init_database(self):
        """إنشاء الجداول إذا لم تكن موجودة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                # جدول المستخدمين
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    first_name TEXT,
                    last_name TEXT,
                    join_date TEXT,
                    message_count INTEGER DEFAULT 0,
                    last_active TEXT,
                    is_admin BOOLEAN DEFAULT 0
                )
                ''')
                
                # جدول الإذاعات
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS broadcasts (
                    broadcast_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    admin_id INTEGER,
                    message_text TEXT,
                    sent_date TEXT,
                    recipients_count INTEGER
                )
                ''')
                
                # جدول سجلات النشاط
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS activity_logs (
                    log_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    action TEXT,
                    timestamp TEXT,
                    details TEXT
                )
                ''')
                
                # ==================== جداول الذكاء الاصطناعي ====================
                
                # جدول استخدام الذكاء الاصطناعي
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    service_type TEXT,
                    usage_date TEXT,
                    usage_count INTEGER DEFAULT 0,
                    UNIQUE(user_id, service_type, usage_date),
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                ''')
                
                # جدول محادثات الذكاء الاصطناعي
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_conversations (
                    conversation_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    service_type TEXT,
                    user_message TEXT,
                    ai_response TEXT,
                    timestamp TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                ''')
                
                # جدول الملفات المولدة (صور وفيديوهات)
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS ai_generated_files (
                    file_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    file_type TEXT,  -- image/video
                    prompt TEXT,
                    file_url TEXT,
                    thumbnail_url TEXT,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                ''')
                
                # جدول الإشعارات (اختياري للمستقبل)
                cursor.execute('''
                CREATE TABLE IF NOT EXISTS notifications (
                    notification_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    notification_type TEXT,
                    title TEXT,
                    message TEXT,
                    is_read BOOLEAN DEFAULT 0,
                    created_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
                ''')
                
                conn.commit()
                logger.info("✅ قاعدة البيانات جاهزة مع دعم الذكاء الاصطناعي")
                
        except Exception as e:
            logger.error(f"❌ خطأ في تهيئة قاعدة البيانات: {e}")
    
    # ==================== دوال المستخدمين ====================
    def add_or_update_user(self, user_id, username, first_name, last_name=None):
        """إضافة أو تحديث مستخدم"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                current_time = datetime.now().isoformat()
                
                # تحقق إذا كان المستخدم موجوداً
                cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
                existing_user = cursor.fetchone()
                
                if existing_user:
                    # تحديث المستخدم الموجود
                    cursor.execute('''
                    UPDATE users 
                    SET username=?, first_name=?, last_name=?, last_active=?
                    WHERE user_id=?
                    ''', (username, first_name, last_name, current_time, user_id))
                    
                    # زيادة عداد الرسائل
                    cursor.execute('''
                    UPDATE users 
                    SET message_count = message_count + 1 
                    WHERE user_id = ?
                    ''', (user_id,))
                else:
                    # إضافة مستخدم جديد
                    cursor.execute('''
                    INSERT INTO users 
                    (user_id, username, first_name, last_name, join_date, last_active, message_count)
                    VALUES (?, ?, ?, ?, ?, ?, 1)
                    ''', (user_id, username, first_name, last_name, current_time, current_time))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في إضافة/تحديث المستخدم: {e}")
            return False
    
    def get_user(self, user_id):
        """الحصول على معلومات مستخدم"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
                user = cursor.fetchone()
                return dict(user) if user else None
        except Exception as e:
            logger.error(f"❌ خطأ في جلب بيانات المستخدم: {e}")
            return None
    
    def get_all_users(self):
        """الحصول على جميع المستخدمين"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT * FROM users ORDER BY join_date DESC")
                users = cursor.fetchall()
                return [dict(user) for user in users]
        except Exception as e:
            logger.error(f"❌ خطأ في جلب جميع المستخدمين: {e}")
            return []
    
    def get_users_count(self):
        """الحصول على عدد المستخدمين - موثوق 100%"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ خطأ في جلب عدد المستخدمين: {e}")
            return 0
    
    def get_active_users_count(self, days=7):
        """الحصول على عدد المستخدمين النشطين"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                cursor.execute('''
                SELECT COUNT(*) FROM users 
                WHERE last_active >= ?
                ''', (cutoff_date,))
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ خطأ في جلب المستخدمين النشطين: {e}")
            return 0
    
    # ==================== دوال الإذاعة ====================
    def add_broadcast(self, admin_id, message_text, recipients_count):
        """تسجيل إذاعة جديدة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                current_time = datetime.now().isoformat()
                
                cursor.execute('''
                INSERT INTO broadcasts (admin_id, message_text, sent_date, recipients_count)
                VALUES (?, ?, ?, ?)
                ''', (admin_id, message_text, current_time, recipients_count))
                
                conn.commit()
                broadcast_id = cursor.lastrowid
                logger.info(f"✅ تم حفظ إذاعة #{broadcast_id}")
                return broadcast_id
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل الإذاعة: {e}")
            return None
    
    def get_broadcasts(self, limit=10):
        """الحصول على آخر الإذاعات"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT b.*, u.first_name as admin_name 
                FROM broadcasts b
                LEFT JOIN users u ON b.admin_id = u.user_id
                ORDER BY sent_date DESC
                LIMIT ?
                ''', (limit,))
                broadcasts = cursor.fetchall()
                return [dict(broadcast) for broadcast in broadcasts]
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الإذاعات: {e}")
            return []
    
    def get_broadcast_stats(self, broadcast_id):
        """الحصول على إحصائيات إذاعة محددة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT * FROM broadcasts WHERE broadcast_id = ?
                ''', (broadcast_id,))
                broadcast = cursor.fetchone()
                return dict(broadcast) if broadcast else None
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات الإذاعة: {e}")
            return None
    
    # ==================== دوال الذكاء الاصطناعي ====================
    
    def log_ai_usage(self, user_id, service_type):
        """تسجيل استخدام خدمة الذكاء الاصطناعي"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                today = datetime.now().strftime('%Y-%m-%d')
                
                cursor.execute('''
                INSERT INTO ai_usage (user_id, service_type, usage_date, usage_count)
                VALUES (?, ?, ?, 1)
                ON CONFLICT(user_id, service_type, usage_date) 
                DO UPDATE SET usage_count = usage_count + 1
                ''', (user_id, service_type, today))
                
                conn.commit()
                return True
                
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل استخدام AI: {e}")
            return False
    
    def get_ai_usage_stats(self, user_id=None, date=None):
        """الحصول على إحصائيات استخدام الذكاء الاصطناعي"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                if date is None:
                    date = datetime.now().strftime('%Y-%m-%d')
                
                if user_id:
                    # إحصائيات مستخدم محدد
                    cursor.execute('''
                    SELECT service_type, SUM(usage_count) as total_usage
                    FROM ai_usage 
                    WHERE user_id = ? AND usage_date = ?
                    GROUP BY service_type
                    ''', (user_id, date))
                else:
                    # إحصائيات جميع المستخدمين
                    cursor.execute('''
                    SELECT service_type, SUM(usage_count) as total_usage
                    FROM ai_usage 
                    WHERE usage_date = ?
                    GROUP BY service_type
                    ''', (date,))
                
                results = cursor.fetchall()
                stats = {}
                for row in results:
                    stats[row[0]] = row[1]
                
                return stats
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إحصائيات AI: {e}")
            return {}
    
    def get_ai_users_count(self):
        """الحصول على عدد المستخدمين الذين استخدموا الذكاء الاصطناعي"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT COUNT(DISTINCT user_id) FROM ai_usage
                ''')
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ خطأ في جلب عدد مستخدمي AI: {e}")
            return 0
    
    def save_ai_conversation(self, user_id, service_type, user_message, ai_response):
        """حفظ محادثة الذكاء الاصطناعي"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                timestamp = datetime.now().isoformat()
                
                cursor.execute('''
                INSERT INTO ai_conversations 
                (user_id, service_type, user_message, ai_response, timestamp)
                VALUES (?, ?, ?, ?, ?)
                ''', (user_id, service_type, user_message, ai_response, timestamp))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ محادثة AI: {e}")
            return None
    
    def get_user_ai_conversations(self, user_id, limit=20):
        """الحصول على محادثات الذكاء الاصطناعي للمستخدم"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute('''
                SELECT * FROM ai_conversations 
                WHERE user_id = ?
                ORDER BY timestamp DESC
                LIMIT ?
                ''', (user_id, limit))
                
                conversations = cursor.fetchall()
                return [dict(conv) for conv in conversations]
        except Exception as e:
            logger.error(f"❌ خطأ في جلب محادثات AI: {e}")
            return []
    
    def save_generated_file(self, user_id, file_type, prompt, file_url, thumbnail_url=None):
        """حفظ معلومات الملف المولد"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                created_at = datetime.now().isoformat()
                
                cursor.execute('''
                INSERT INTO ai_generated_files 
                (user_id, file_type, prompt, file_url, thumbnail_url, created_at)
                VALUES (?, ?, ?, ?, ?, ?)
                ''', (user_id, file_type, prompt, file_url, thumbnail_url, created_at))
                
                conn.commit()
                return cursor.lastrowid
                
        except Exception as e:
            logger.error(f"❌ خطأ في حفظ الملف المولد: {e}")
            return None
    
    def get_user_generated_files(self, user_id, file_type=None, limit=10):
        """الحصول على الملفات المولدة للمستخدم"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = '''
                SELECT * FROM ai_generated_files 
                WHERE user_id = ?
                '''
                params = [user_id]
                
                if file_type:
                    query += ' AND file_type = ?'
                    params.append(file_type)
                
                query += ' ORDER BY created_at DESC LIMIT ?'
                params.append(limit)
                
                cursor.execute(query, params)
                files = cursor.fetchall()
                return [dict(file) for file in files]
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الملفات المولدة: {e}")
            return []
    
    def get_total_generated_files(self, file_type=None):
        """الحصول على إجمالي الملفات المولدة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                
                query = 'SELECT COUNT(*) FROM ai_generated_files'
                params = []
                
                if file_type:
                    query += ' WHERE file_type = ?'
                    params.append(file_type)
                
                cursor.execute(query, params)
                result = cursor.fetchone()
                return result[0] if result else 0
                
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إجمالي الملفات: {e}")
            return 0
    
    # ==================== دوال الإحصائيات ====================
    def get_stats_simple(self):
        """الحصول على إحصائيات مبسطة"""
        try:
            stats = {}
            
            # عدد المستخدمين
            stats['total_users'] = self.get_users_count()
            
            # عدد الرسائل
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(message_count) FROM users")
                result = cursor.fetchone()[0]
                stats['total_messages'] = int(result) if result else 0
            
            # عدد الإذاعات
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM broadcasts")
                stats['total_broadcasts'] = cursor.fetchone()[0] or 0
            
            # المستخدمين الجدد اليوم
            with self.get_connection() as conn:
                cursor = conn.cursor()
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute("SELECT COUNT(*) FROM users WHERE join_date LIKE ?", (f'{today}%',))
                stats['new_users_today'] = cursor.fetchone()[0] or 0
            
            # آخر إذاعة
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(broadcast_id) FROM broadcasts")
                stats['last_broadcast_id'] = cursor.fetchone()[0]
            
            # إحصائيات الذكاء الاصطناعي
            stats['ai_users'] = self.get_ai_users_count()
            stats['ai_chats'] = self.get_total_ai_conversations()
            stats['ai_images'] = self.get_total_generated_files('image')
            stats['ai_videos'] = self.get_total_generated_files('video')
            
            logger.info(f"✅ الإحصائيات المبسطة المحسوبة: {stats}")
            return stats
            
        except Exception as e:
            logger.error(f"❌ خطأ في جلب الإحصائيات المبسطة: {e}")
            return {
                'total_users': self.get_users_count(),
                'total_messages': 0,
                'total_broadcasts': 0,
                'new_users_today': 0,
                'last_broadcast_id': None,
                'ai_users': 0,
                'ai_chats': 0,
                'ai_images': 0,
                'ai_videos': 0
            }
    
    def get_stats_fixed(self):
        """إحصائيات موثوقة 100% - لا تعطي أي أخطاء"""
        try:
            logger.info("🔍 بدء جمع الإحصائيات الموثوقة...")
            stats = {}
            
            # 1. عدد المستخدمين - الطريقة الأكيدة
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM users")
                result = cursor.fetchone()
                stats['total_users'] = result[0] if result else 0
            
            logger.info(f"👥 عدد المستخدمين: {stats['total_users']}")
            
            # 2. عدد الرسائل
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT SUM(message_count) FROM users")
                result = cursor.fetchone()
                total = result[0] if result else 0
                stats['total_messages'] = int(total) if total else 0
            
            logger.info(f"💬 عدد الرسائل: {stats['total_messages']}")
            
            # 3. عدد الإذاعات
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM broadcasts")
                result = cursor.fetchone()
                stats['total_broadcasts'] = result[0] if result else 0
            
            logger.info(f"📢 عدد الإذاعات: {stats['total_broadcasts']}")
            
            # 4. آخر إذاعة
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT MAX(broadcast_id) FROM broadcasts")
                result = cursor.fetchone()
                stats['last_broadcast_id'] = result[0] if result else None
            
            # 5. المستخدمين الجدد اليوم
            with self.get_connection() as conn:
                cursor = conn.cursor()
                today = datetime.now().strftime('%Y-%m-%d')
                cursor.execute("SELECT COUNT(*) FROM users WHERE join_date LIKE ?", (f'{today}%',))
                result = cursor.fetchone()
                stats['new_users_today'] = result[0] if result else 0
            
            logger.info(f"🆕 مستخدمين جدد اليوم: {stats['new_users_today']}")
            
            # 6. المستخدمين الأكثر نشاطاً
            try:
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute('''
                    SELECT first_name, message_count 
                    FROM users 
                    ORDER BY message_count DESC 
                    LIMIT 5
                    ''')
                    top_users = cursor.fetchall()
                    stats['top_users'] = [dict(row) for row in top_users]
            except Exception as top_error:
                logger.warning(f"⚠️ خطأ في جلب المستخدمين النشطين: {top_error}")
                stats['top_users'] = []
            
            # 7. إحصائيات الذكاء الاصطناعي
            try:
                stats['ai_users'] = self.get_ai_users_count()
                stats['ai_chats'] = self.get_total_ai_conversations()
                stats['ai_images'] = self.get_total_generated_files('image')
                stats['ai_videos'] = self.get_total_generated_files('video')
                
                # استخدام اليوم
                today_stats = self.get_ai_usage_stats(date=datetime.now().strftime('%Y-%m-%d'))
                stats['ai_usage_today'] = today_stats
                
                logger.info(f"🤖 إحصائيات AI: {stats['ai_users']} مستخدم، {stats['ai_chats']} محادثة")
                
            except Exception as ai_error:
                logger.warning(f"⚠️ خطأ في إحصائيات AI: {ai_error}")
                stats['ai_users'] = 0
                stats['ai_chats'] = 0
                stats['ai_images'] = 0
                stats['ai_videos'] = 0
                stats['ai_usage_today'] = {}
            
            logger.info(f"✅ الإحصائيات الموثوقة المحسوبة بنجاح")
            return stats
            
        except Exception as e:
            logger.error(f"❌ خطأ في get_stats_fixed: {e}", exc_info=True)
            # إرجاع قيم أساسية مضمونة
            return {
                'total_users': self.get_users_count(),
                'total_messages': 0,
                'total_broadcasts': 0,
                'last_broadcast_id': None,
                'new_users_today': 0,
                'top_users': [],
                'ai_users': 0,
                'ai_chats': 0,
                'ai_images': 0,
                'ai_videos': 0,
                'ai_usage_today': {}
            }
    
    def get_total_ai_conversations(self):
        """الحصول على إجمالي عدد محادثات الذكاء الاصطناعي"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cursor.execute("SELECT COUNT(*) FROM ai_conversations")
                result = cursor.fetchone()
                return result[0] if result else 0
        except Exception as e:
            logger.error(f"❌ خطأ في جلب إجمالي محادثات AI: {e}")
            return 0
    
    def get_stats(self):
        """الدالة الرئيسية للإحصائيات (للتوافق)"""
        # نستخدم النسخة الموثوقة
        return self.get_stats_fixed()
    
    # ==================== دوال النشاط ====================
    def log_activity(self, user_id, action, details=None):
        """تسجيل نشاط المستخدم"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                current_time = datetime.now().isoformat()
                
                cursor.execute('''
                INSERT INTO activity_logs (user_id, action, timestamp, details)
                VALUES (?, ?, ?, ?)
                ''', (user_id, action, current_time, details))
                
                conn.commit()
                return True
        except Exception as e:
            logger.error(f"❌ خطأ في تسجيل النشاط: {e}")
            return False
    
    # ==================== دوال النسخ الاحتياطي ====================
    def backup_database(self, backup_name=None):
        """إنشاء نسخة احتياطية من قاعدة البيانات"""
        import shutil
        
        try:
            if backup_name is None:
                backup_name = f"backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            
            shutil.copy2(self.db_name, backup_name)
            logger.info(f"✅ تم إنشاء نسخة احتياطية: {backup_name}")
            return backup_name
        except Exception as e:
            logger.error(f"❌ خطأ في إنشاء النسخة الاحتياطية: {e}")
            return None
    
    def cleanup_old_data(self, days=30):
        """تنظيف البيانات القديمة"""
        try:
            with self.get_connection() as conn:
                cursor = conn.cursor()
                cutoff_date = (datetime.now() - timedelta(days=days)).isoformat()
                
                deleted_count = 0
                
                # تنظيف سجلات النشاط القديمة
                cursor.execute('''
                DELETE FROM activity_logs 
                WHERE timestamp < ?
                ''', (cutoff_date,))
                deleted_count += cursor.rowcount
                
                # تنظيف محادثات AI القديمة (احتفظ بـ 7 أيام فقط)
                ai_cutoff = (datetime.now() - timedelta(days=7)).isoformat()
                cursor.execute('''
                DELETE FROM ai_conversations 
                WHERE timestamp < ?
                ''', (ai_cutoff,))
                deleted_count += cursor.rowcount
                
                conn.commit()
                logger.info(f"✅ تم تنظيف {deleted_count} سجل قديم")
                return deleted_count
        except Exception as e:
            logger.error(f"❌ خطأ في تنظيف البيانات القديمة: {e}")
            return 0
    
    def get_database_info(self):
        """الحصول على معلومات عن قاعدة البيانات"""
        try:
            import os
            info = {
                'filename': self.db_name,
                'exists': os.path.exists(self.db_name),
                'size': 0,
                'tables': []
            }
            
            if info['exists']:
                info['size'] = os.path.getsize(self.db_name)
                
                with self.get_connection() as conn:
                    cursor = conn.cursor()
                    cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
                    info['tables'] = [row[0] for row in cursor.fetchall()]
            
            return info
        except Exception as e:
            logger.error(f"❌ خطأ في جلب معلومات قاعدة البيانات: {e}")
            return {'filename': self.db_name, 'exists': False}

# إنشاء كائن قاعدة بيانات عالمي
db = Database()