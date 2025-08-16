from flask import Flask, render_template, jsonify, request, flash, redirect, url_for, send_from_directory
import string
import secrets
from datetime import datetime
from urllib.parse import quote
import os
from pymongo import MongoClient
from flask_login import LoginManager, UserMixin, login_required, login_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from bson import ObjectId
from dotenv import load_dotenv

load_dotenv() 

app = Flask(__name__)
app.secret_key = os.getenv('SECRET_KEY')

# Inisialisasi Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'admin_login'

# User Model untuk Flask-Login
class User(UserMixin):
    def __init__(self, username):
        self.id = username

# User loader untuk Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User(user_id)

# Konfigurasi MongoDB
client = MongoClient(os.getenv('MONGODB_URI'))
db = client[os.getenv('DB_NAME')]  # Nama database
orders = db['orders']  # Nama collection
admins = db['admins']  # Nama collection

# Konfigurasi upload folder
UPLOAD_FOLDER = '/tmp/uploads'
UPLOAD_FOLDER_FINISH = '/tmp/finish'

# Buat folder upload jika belum ada
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(UPLOAD_FOLDER_FINISH, exist_ok=True)

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['UPLOAD_FOLDER_FINISH'] = UPLOAD_FOLDER_FINISH
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # Batas maksimal 16MB

# Fungsi generate order code
def generate_order_code(length=8):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(length))

# Function to get status color
def get_status_color(status):
    status_map = {
        'Menunggu': 'bg-yellow-100 text-yellow-800',
        'Diproses': 'bg-blue-100 text-blue-800',
        'Selesai': 'bg-green-100 text-green-800',
        'Dibatalkan': 'bg-red-100 text-red-800',
        'Ditolak': 'bg-gray-100 text-gray-800'
    }
    return status_map.get(status, 'bg-gray-100 text-gray-800')

# Function to format currency
def format_currency(value):
    try:
        return "{:,}".format(int(value)).replace(",", ".")
    except (ValueError, TypeError):
        return "0"

# Register the function to Jinja2
app.jinja_env.filters['getStatusColor'] = get_status_color
app.jinja_env.filters['format_currency'] = format_currency

# Fungsi untuk membersihkan nama file
def secure_filename(filename):
    # Hanya izinkan karakter alfanumerik, titik, garis bawah, dan strip
    import re
    filename = re.sub(r'[^\w\-_.]', '', filename)
    return filename

# Home route
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Ambil data dari form
        order_data = {
            'nama': request.form['nama'],
            'harga': 0,
            'jenis': request.form['jenis'],
            'deadline': request.form['deadline'],
            'deskripsi': request.form['deskripsi'],
            'wa_pengguna': request.form['wa'],
            'order_code': generate_order_code(),
            'status': 'Menunggu',  # Status default
            'finished_file': '',  # Inisialisasi dengan string kosong
            'created_at': datetime.now(),
            'updated_at': datetime.now()
        }

        # Cek apakah file ada dalam request
        if 'file' not in request.files:
            flash('Tidak ada file yang diunggah', 'error')
            return redirect(request.url)
            
        file = request.files['file']
        
        # Jika user tidak memilih file
        if file.filename == '':
            flash('Tidak ada file yang dipilih', 'error')
            return redirect(request.url)
            
        if file:
            try:
                # Buat nama file yang aman
                filename = secure_filename(file.filename)
                # Tambahkan timestamp untuk menghindari konflik nama file
                filename = f"{int(datetime.now().timestamp())}_{filename}"
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                
                # Simpan file
                file.save(filepath)
                
                # Simpan path file relatif ke database
                order_data['file_path'] = filename
                
                # Simpan data order ke database
                result = orders.insert_one(order_data)
                
                flash('Pesanan berhasil dibuat! Kode pesanan Anda: ' + order_data['order_code'], 'success')
                return redirect(url_for('cek_order', order_code=order_data['order_code']))
                
            except Exception as e:
                app.logger.error(f"Error saat mengunggah file: {str(e)}")
                flash('Terjadi kesalahan saat mengunggah file', 'error')
                return redirect(request.url)
    
    return render_template('index.html')


# Cek Order 
@app.route('/cek-order', methods=['POST'])
def cek_order():
    try:
        kode_order = request.form.get('kode_order')
        if not kode_order:
            return jsonify({
                'status': 'error',
                'message': 'Kode order tidak boleh kosong.'
            }), 400
            
        print(f"Mencari order dengan kode: {kode_order}")  # Log ke terminal
        
        # Cari order berdasarkan kode
        order = orders.find_one({'order_code': kode_order})
        
        if order:
            print(f"Order ditemukan: {order}")  # Log order yang ditemukan
            # Konversi ObjectId ke string agar bisa di-serialize ke JSON
            order['_id'] = str(order['_id'])
            # Konversi datetime ke string
            if 'created_at' in order and order['created_at']:
                order['created_at'] = order['created_at'].strftime('%d %B %Y %H:%M')
            if 'updated_at' in order and order['updated_at']:
                order['updated_at'] = order['updated_at'].strftime('%d %B %Y %H:%M')
                
            return jsonify({
                'status': 'success',
                'order': order
            })
        else:
            print(f"Order dengan kode {kode_order} tidak ditemukan")  # Log order tidak ditemukan
            return jsonify({
                'status': 'error',
                'message': 'Order tidak ditemukan. Pastikan kode order benar.'
            }), 404
            
    except Exception as e:
        print(f"Error saat memeriksa order: {str(e)}")  # Log error ke terminal
        return jsonify({
            'status': 'error',
            'message': f'Terjadi kesalahan server: {str(e)}'
        }), 500


@app.route('/admin')
@login_required
def view():
    # Ambil semua pesanan dari database
    orders_list = list(orders.find())
    return render_template('admin.html', orders=orders_list)



@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        # Find admin in MongoDB
        admin = admins.find_one({'username': username})
        
        if admin and check_password_hash(admin['password'], password):
            user = User(username)
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('view'))
        else:
            flash('Invalid username or password', 'error')
    
    return render_template('login_admin.html')

@app.route('/admin/logout')
@login_required
def admin_logout():
    logout_user()
    return redirect(url_for('admin_login'))

@app.route('/admin/orders/<order_id>')
@login_required
def get_order(order_id):
    try:
        order = orders.find_one({'_id': ObjectId(order_id)})
        if order:
            # Convert ObjectId to string for JSON serialization
            order['_id'] = str(order['_id'])
            # Convert datetime to string if it exists
            if 'created_at' in order and order['created_at']:
                order['created_at'] = order['created_at'].strftime('%Y-%m-%d %H:%M:%S')
            if 'updated_at' in order and order['updated_at']:
                order['updated_at'] = order['updated_at'].strftime('%Y-%m-%d %H:%M:%S')
            return jsonify({'status': 'success', 'order': order})
        else:
            return jsonify({'status': 'error', 'message': 'Order not found'}), 404
    except Exception as e:
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/admin/orders/<order_id>/update', methods=['POST'])
@login_required
def update_order(order_id):
    try:
        print("\n=== DEBUG: Mulai update order ===")
        print("Request files:", request.files)
        print("Request form:", request.form)
        
        data = request.form
        order_data = orders.find_one({'_id': ObjectId(order_id)})
        
        if not order_data:
            print("Error: Order tidak ditemukan")
            return jsonify({'status': 'error', 'message': 'Order not found'}), 404
        
        # Inisialisasi update_data dengan nilai default
        update_data = {
            'status': data.get('status', 'Menunggu'),
            'harga': data.get('harga', 0),
            'updated_at': datetime.now()
        }

        # Handle file upload
        if 'finishedFile' in request.files:
            file = request.files['finishedFile']
            print(f"File received: {file.filename}")
            
            if file and file.filename != '':
                # Dapatkan ekstensi file asli
                file_ext = os.path.splitext(file.filename)[1].lower()
                print(f"File extension: {file_ext}")
                
                # Buat nama file dengan format: kode_pesanan_timestamp.ekstensi
                timestamp = int(datetime.now().timestamp())
                filename = f"{order_data['order_code']}_Finish{file_ext}"
                
                # Path lengkap untuk menyimpan file
                upload_dir = os.path.join('static', 'finish')
                os.makedirs(upload_dir, exist_ok=True)  # Pastikan folder ada
                filepath = os.path.join(upload_dir, filename)
                
                print(f"Saving to: {filepath}")
                
                try:
                    # Simpan file
                    file.save(filepath)
                    print("File saved successfully")
                    
                    # Update path file di database (simpan path relatif)
                    update_data['finished_file'] = f"static/finish/{filename}"
                    print(f"File akan disimpan di database sebagai: {update_data['finished_file']}")
                    
                    # Hapus file lama jika ada
                    old_file = order_data.get('finished_file', '')
                    if old_file:
                        old_filepath = os.path.join('static', old_file)
                        if os.path.exists(old_filepath):
                            try:
                                os.remove(old_filepath)
                                print(f"Old file deleted: {old_filepath}")
                            except Exception as e:
                                print(f"Gagal menghapus file lama {old_filepath}: {str(e)}")
                    
                except Exception as e:
                    print(f"Error saving file: {str(e)}")
                    return jsonify({
                        'status': 'error',
                        'message': f'Gagal menyimpan file: {str(e)}',
                        'error_type': type(e).__name__
                    }), 500
        
        # Update order di database
        print(f"Updating database with: {update_data}")
        result = orders.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': update_data}
        )
        
        # Ambil data terbaru untuk memastikan
        updated_order = orders.find_one({'_id': ObjectId(order_id)})
        print(f"Updated order data: {updated_order}")
        print("=== DEBUG: Update selesai ===\n")
        
        return jsonify({
            'status': 'success',
            'message': 'Order berhasil diperbarui',
            'data': {
                'order_id': str(updated_order['_id']),
                'status': update_data['status'],
                'finished_file': updated_order.get('finished_file', '')
            }
        })
        
    except Exception as e:
        print(f"Unexpected error: {str(e)}")
        print(f"Error type: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error', 
            'message': f'Terjadi kesalahan: {str(e)}',
            'error_type': type(e).__name__
        }), 500

@app.route('/admin/orders/<order_id>/download')
@login_required
def download_file(order_id):
    try:
        order = orders.find_one({'_id': ObjectId(order_id)})
        if not order or 'file_path' not in order:
            flash('File tidak ditemukan', 'error')
            return redirect(url_for('admin'))
            
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], order['file_path'])
        
        # Pastikan file ada
        if not os.path.exists(file_path):
            flash('File tidak ditemukan di server', 'error')
            return redirect(url_for('admin'))
            
        # Dapatkan ekstensi file asli
        file_ext = os.path.splitext(order['file_path'])[1]
        # Nama file untuk diunduh
        download_name = f"{order['nama']}_{order['order_code']}{file_ext}"
        
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            order['file_path'],
            as_attachment=True,
            download_name=download_name
        )
        
    except Exception as e:
        app.logger.error(f"Error saat mengunduh file: {str(e)}")
        flash('Terjadi kesalahan saat mengunduh file', 'error')
        return redirect(url_for('admin'))

@app.route('/download/<order_id>')
def download_file(order_id):
    try:
        order = orders.find_one({'_id': ObjectId(order_id)})
        if not order or 'file_path' not in order:
            flash('File tidak ditemukan', 'error')
            return redirect(url_for('admin'))
            
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], order['file_path'])
        
        # Pastikan file ada
        if not os.path.exists(file_path):
            flash('File tidak ditemukan di server', 'error')
            return redirect(url_for('admin'))
            
        # Dapatkan ekstensi file asli
        file_ext = os.path.splitext(order['file_path'])[1]
        # Nama file untuk diunduh
        download_name = f"{order['nama']}_{order['order_code']}{file_ext}"
        
        return send_from_directory(
            app.config['UPLOAD_FOLDER'],
            order['file_path'],
            as_attachment=True,
            download_name=download_name
        )
        
    except Exception as e:
        app.logger.error(f"Error saat mengunduh file: {str(e)}")
        flash('Terjadi kesalahan saat mengunduh file', 'error')
        return redirect(url_for('admin'))

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    if not os.path.exists(app.config['UPLOAD_FOLDER_FINISH']):
        os.makedirs(app.config['UPLOAD_FOLDER_FINISH'], exist_ok=True) 
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)