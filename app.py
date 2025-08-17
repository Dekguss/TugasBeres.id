from flask import Flask, render_template, jsonify, request, flash, redirect, url_for, send_from_directory
import string
import secrets
from datetime import datetime
from urllib.parse import quote
import os
import json
from bson.objectid import ObjectId
from flask_pymongo import PyMongo
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from dotenv import load_dotenv
import cloudinary
import cloudinary.uploader
import cloudinary.api

# Load environment variables
load_dotenv()

# Konfigurasi Cloudinary
cloudinary.config(
    cloud_name=os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key=os.getenv('CLOUDINARY_API_KEY'),
    api_secret=os.getenv('CLOUDINARY_API_SECRET'),
    secure=True
)

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
app.config['UPLOAD_FOLDER'] = '/tmp/uploads'  # Gunakan /tmp di Vercel
app.config['UPLOAD_FOLDER_FINISH'] = '/tmp/finish'  # Gunakan /tmp di Vercel

# Buat folder upload jika belum ada
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['UPLOAD_FOLDER_FINISH'], exist_ok=True)

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

        # Simpan file jika ada
        file = request.files['file']
        if file and file.filename != '':
            # Dapatkan ekstensi file asli
            file_ext = os.path.splitext(file.filename)[1]  # Contoh: '.pdf', '.docx', dll
            # Buat nama file baru dengan format: kode_pesanan_nama.ekstensi
            filename = f"{order_data['order_code']}_{order_data['nama']}{file_ext}"
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            
            # Simpan file
            file.save(filepath)
            order_data['file_path'] = filepath
            order_data['file_name'] = filename
            order_data['file_extension'] = file_ext.lower()  # Simpan ekstensi file juga

        try:
            # Simpan ke MongoDB
            result = orders.insert_one(order_data)
            order_id = str(result.inserted_id)
            
            # Format pesan WhatsApp
            pesan = f'''
Halo Admin, saya baru saja mengirim tugas:

Kode Pemesanan: {order_data['order_code']}
Nama: {order_data['nama']}
Jenis Tugas: {order_data['jenis']}
Deadline: {order_data['deadline']}
WA Saya: {order_data['wa_pengguna']}
Deskripsi: {order_data['deskripsi']}

Mohon segera dicek ya 🙏
            '''
            pesan_encoded = quote(pesan)
            return redirect(f'https://wa.me/6281529808370?text={pesan_encoded}')

        # Jika terjadi kesalahan
        except Exception as e:
            flash('Terjadi kesalahan saat menyimpan data. Silakan coba lagi.')
            return redirect(url_for('index'))

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

@app.route('/admin/orders/<order_id>', methods=['PUT'])
@login_required
def update_order(order_id):
    try:
        data = request.form
        order_data = orders.find_one({'_id': ObjectId(order_id)})
        
        if not order_data:
            return jsonify({'status': 'error', 'message': 'Order tidak ditemukan'}), 404
        
        update_data = {
            'status': data.get('status', 'Menunggu'),
            'harga': data.get('harga', 0),
            'updated_at': datetime.now()
        }

        # Handle file upload
        if 'finishedFile' in request.files:
            file = request.files['finishedFile']
            if file.filename != '':
                try:
                    # Upload ke Cloudinary
                    upload_result = cloudinary.uploader.upload(
                        file,
                        folder="tugas_beres",  # Folder di Cloudinary
                        resource_type="auto"
                    )
                    
                    # Simpan URL file dan public_id ke database
                    update_data['file_url'] = upload_result['secure_url']
                    update_data['file_public_id'] = upload_result['public_id']
                    
                except Exception as e:
                    print(f"Error uploading to Cloudinary: {str(e)}")
                    return jsonify({'status': 'error', 'message': 'Gagal mengupload file'}), 500

        # Update data di database
        orders.update_one(
            {'_id': ObjectId(order_id)},
            {'$set': update_data}
        )
        
        return jsonify({'status': 'success', 'message': 'Order berhasil diupdate'})
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/admin/orders/<order_id>/download')
@login_required
def download_file(order_id):
    try:
        order = orders.find_one({'_id': ObjectId(order_id)})
        if not order or 'file_url' not in order:
            return jsonify({'status': 'error', 'message': 'File tidak ditemukan'}), 404
            
        # Redirect ke URL file di Cloudinary
        return redirect(order['file_url'])
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Gagal mendownload file'}), 500

@app.route('/admin/orders/<order_id>/delete_file', methods=['DELETE'])
@login_required
def delete_file(order_id):
    try:
        order = orders.find_one({'_id': ObjectId(order_id)})
        if not order or 'file_public_id' not in order:
            return jsonify({'status': 'error', 'message': 'File tidak ditemukan'}), 404
            
        # Hapus file dari Cloudinary
        cloudinary.uploader.destroy(order['file_public_id'])
        
        # Update data di database
        orders.update_one(
            {'_id': ObjectId(order_id)},
            {'$unset': {'file_url': '', 'file_public_id': ''}}
        )
        
        return jsonify({'status': 'success', 'message': 'File berhasil dihapus'})
        
    except Exception as e:
        print(f"Error: {str(e)}")
        return jsonify({'status': 'error', 'message': 'Gagal menghapus file'}), 500

if __name__ == '__main__':
    if not os.path.exists(app.config['UPLOAD_FOLDER']):
        os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    if not os.path.exists(app.config['UPLOAD_FOLDER_FINISH']):
        os.makedirs(app.config['UPLOAD_FOLDER_FINISH'], exist_ok=True) 
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)