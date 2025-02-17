# ایمپورت کتابخانه‌های مورد نیاز
import flask  # برای ایجاد اپلیکیشن وب
from flask_sqlalchemy import SQLAlchemy  # برای مدیریت دیتابیس SQLAlchemy
from geoalchemy2 import Geometry, WKTElement  # برای مدیریت هندسه در PostGIS
from geoalchemy2.shape import to_shape  # برای تبدیل داده‌های هندسی به اشکال قابل استفاده
import os  # برای مدیریت مقادیر محیطی
from sqlalchemy.sql import text  # برای اجرای کوئری‌های SQL خام

# ایجاد یک اپلیکیشن Flask
app = flask.Flask(__name__)  # تعریف اپلیکیشن اصلی Flask

# تنظیم کلید رمز تصادفی برای جلسات (برای امنیت)
app.secret_key = os.urandom(24)  # از یک کلید random برای session استفاده می‌شود

# تنظیمات اتصال به پایگاه داده PostgreSQL
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:51527581@localhost/map_project'  # آدرس پایگاه داده
db = SQLAlchemy(app)  # ایجاد یک نمونه SQLAlchemy برای مدیریت پایگاه داده

# تعریف مدل جدول کاربران در پایگاه داده
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)  # کلید اصلی (شناسه کاربر)
    username = db.Column(db.String(120), unique=True, nullable=False)  # نام کاربری منحصربه‌فرد
    password = db.Column(db.String(120), nullable=False)  # رمز عبور
    email = db.Column(db.String(120), unique=True, nullable=False)  # ایمیل منحصربه‌فرد

# ایجاد جداول در پایگاه داده (فقط در صورتی که از قبل وجود نداشته باشند)
with app.app_context():
    db.create_all()  # ایجاد تمام جداول تعریف شده در مدل‌های پایگاه داده

# تعریف مسیر (Route) صفحه اصلی
@app.route('/')
def map():
    if 'username' not in flask.session:  # بررسی اینکه آیا کاربر وارد سیستم شده است یا خیر
        return flask.redirect(flask.url_for('login'))  # در غیر این صورت به صفحه ورود منتقل می‌شود
    return flask.render_template('map.html')  # در صورت ورود، صفحه نقشه نمایش داده می‌شود

# مسیر ورود کاربر به سیستم
@app.route('/login', methods=['GET', 'POST'])
def login():
    error_message = None  # تعریف متغییر برای ذخیره خطاها
    if flask.request.method == 'POST':  # اگر درخواست POST باشد (ثبت فرم)
        username = flask.request.form.get('username', '').strip()  # دریافت یوزرنیم
        password = flask.request.form.get('password', '').strip()  # دریافت پسورد

        if not username or not password:  # بررسی پر بودن فیلد‌ها
            error_message = "لطفاً تمام فیلدها را پر کنید."  # پیام خطا در صورت خالی بودن فیلدها
        else:
            user = User.query.filter_by(username=username).first()  # جستجوی کاربر در پایگاه داده
            if user and user.password == password:  # بررسی صحت اطلاعات
                flask.session['username'] = user.username  # ذخیره نام‌ کاربری در Session
                return flask.redirect(flask.url_for('map'))  # انتقال به نقشه در صورت موفقیت
            else:
                error_message = "نام کاربری یا کلمه عبور اشتباه است! لطفاً دوباره تلاش کنید."  # پیام خطا در صورت نادرستی اطلاعات

    return flask.render_template('login.html', error_message=error_message)  # نمایش فرم ورود همراه با خطاها (در صورت وجود)

# مسیر ثبت نام کاربران
@app.route('/register', methods=['GET', 'POST'])
def register():
    error_message = None
    if flask.request.method == 'POST':  # اگر درخواست POST باشد (ثبت فرم)
        username = flask.request.form.get('username', '').strip()  # دریافت یوزرنیم
        email = flask.request.form.get('email', '').strip()  # دریافت ایمیل
        password = flask.request.form.get('password', '').strip()  # دریافت پسورد

        if not username or not email or not password:  # بررسی پر بودن فیلدها
            error_message = "لطفاً تمام فیلدها را پر کنید."
        else:
            existing_user = User.query.filter_by(username=username).first()  # بررسی وجود کاربر مشابه
            if existing_user:  # در صورت وجود کاربر
                error_message = "این یوزرنیم قبلاً ثبت شده است! لطفاً یوزرنیم دیگری انتخاب کنید."
            else:
                new_user = User(username=username, email=email, password=password)  # ایجاد کاربر جدید
                db.session.add(new_user)  # اضافه کردن به پایگاه داده
                db.session.commit()  # ثبت تغییرات
                return flask.render_template('map.html')  # هدایت به صفحه نقشه پس از موفقیت

    return flask.render_template('register.html', error_message=error_message)  # نمایش فرم ثبت نام همراه با خطاها (در صورت وجود)

# مسیر خروج از سیستم
@app.route('/logout')
def logout():
    flask.session.pop('username', None)  # حذف Session
    return flask.render_template('logout.html')  # نمایش صفحه Logout

# مسیر افزودن رستوران جدید به نقشه
@app.route('/add-restaurant', methods=['GET', 'POST'])
def add_restaurant():
    if 'username' not in flask.session:  # بررسی ورود به سیستم
        return flask.redirect(flask.url_for('login'))  # هدایت به صفحه ورود در صورت عدم ورود به سیستم

    if flask.request.method == 'GET':  # اگر درخواست GET باشد (صفحه)
        lat = flask.request.args.get('lat', type=float)  # گرفتن عرض جغرافیایی از URL
        lon = flask.request.args.get('lon', type=float)  # گرفتن طول جغرافیایی از URL
        return flask.render_template('add_restaurant.html', lat=lat, lon=lon)  # نمایش فرم افزودن رستوران همراه با مختصات

    elif flask.request.method == 'POST':  # اگر درخواست POST باشد (ثبت فرم)
        name = flask.request.form.get('name', '').strip()  # دریافت نام
        lat = flask.request.form.get('lat', type=float)  # دریافت عرض جغرافیایی
        lon = flask.request.form.get('lon', type=float)  # دریافت طول جغرافیایی

        if not name or not lat or not lon:  # بررسی پر بودن مقادیر
            return flask.render_template('add_restaurant.html', error="تمام فیلدها الزامی هستند.", lat=lat, lon=lon)

        geom = WKTElement(f'POINT({lon} {lat})', srid=4326)  # تبدیل مختصات به WKT برای ذخیره در PostGIS
        try:
            db.session.execute(  # ذخیره اطلاعات در جدول
                text("INSERT INTO restuarant (name, geom) VALUES (:name, ST_SetSRID(ST_GeomFromText(:geom), 4326))"),
                {'name': name, 'geom': f'POINT({lon} {lat})'},
            )
            db.session.commit()
            return flask.render_template('success.html', message="رستوران با موفقیت ذخیره شد.")  # پیام موفقیت
        except Exception as e:  # مدیریت خطاها
            db.session.rollback()  # بازگرداندن تغییرات در صورت خطا
            return flask.render_template('add_restaurant.html', error=f"خطا در ذخیره اطلاعات: {str(e)}", lat=lat, lon=lon)

# مدیریت ارور 404
@app.errorhandler(404)
def page_not_found(error):
    message = '404 Not Found'
    return flask.render_template('404.html', message=message), 404  # نمایش صفحه خطای 404

# اجرای اپلیکیشن
if __name__ == '__main__':
    app.run(debug=True)  # اجرای اپلیکیشن در حالت Debug


