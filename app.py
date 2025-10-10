from flask import Flask, render_template, request, redirect, url_for, flash, session , jsonify
import sqlite3
from datetime import datetime
from datetime import date

app = Flask(__name__)
app.secret_key = 'dasrath'  

DATABASE = 'users.db'  

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn



@app.route('/')
def index():
    return render_template('login.html')

@app.route('/dashboard')
def dashboard():
    if session.get('user'):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT * FROM users WHERE id = ?", (session['user'],))
        user = cur.fetchone()
        conn.close()
        
        return render_template('dashboard.html', user=user)
    return redirect('/login')

@app.route('/profile')
def profile():
    if 'user_email' not in session:
        return redirect(url_for('login'))

    email = session['user_email']
    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('SELECT fullname, email, mobile, department, employee_id FROM users WHERE email=?', (email,))
    user = cur.fetchone()
    conn.close()

    if user:
      
        user_dict = {
            'fullname': user['fullname'],
            'email': user['email'],
            'mobile': user['mobile'],
           'department': user['department'],
            'employee_id': user['employee_id']
        }
        return render_template('profile.html', user=user_dict)
    else:
        return "User not found"




ADMIN_EMAIL = "admin@gmail.com"
ADMIN_PASSWORD = "admin123"

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email']
        password = request.form['password']

       
        if email == "admin@gmail.com" and password == "admin123":
            session['user'] = 'admin'
            session['user_id'] = 'admin'
            return redirect(url_for('admin_page'))

        
        conn = sqlite3.connect('users.db')
        c = conn.cursor()
        c.execute("SELECT id, email, password FROM users WHERE email = ?", (email,))
        user = c.fetchone()
        conn.close()

        if not user:
            flash("Invalid email", "error")
        elif password != user[2]:  
            flash("Invalid password", "error")
        else:
            session['user_id'] = user[0]
            session['user_email'] = user[1]  
            session['user'] = user[0] 
            return redirect(url_for('dashboard'))
        


    return render_template('login.html')



@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.')
    return redirect('/login')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        fullname = request.form['fullname']
        email = request.form['email']
        mobile = request.form['mobile']
        department = request.form['department']
        employee_id = request.form['employee_id']
        password = request.form['password']
        confirm_password = request.form['confirm_password']

        if password != confirm_password:
            flash(" Passwords do not match.")
            return redirect('/signup')

        conn = get_db_connection()
        cur = conn.cursor()

       
        cur.execute("SELECT * FROM users WHERE email = ? OR employee_id = ?", (email, employee_id))
        existing_user = cur.fetchone()

        if existing_user:
            flash(" User already registered. Please log in.")
            conn.close()
            return redirect('/login')

       
        cur.execute(
            'INSERT INTO users (fullname, email, mobile, department, employee_id, password) VALUES (?, ?, ?, ?, ?, ?)',
            (fullname, email, mobile, department, employee_id, password)
        )
        conn.commit()
        conn.close()

        flash(" Account created! Please log in.")
        return redirect('/login')

    return render_template('signup.html')



@app.route('/visualmap')
def visualmap():
    today_date = date.today().strftime("%Y-%m-%d")
    if 'user_id' not in session:
        flash("Please login first.")
        return redirect('/login')

    conn = get_db_connection()
    cursor = conn.cursor()
    
    
    cursor.execute("""
        SELECT b1.seat_no, b1.status 
        FROM bookings b1
        INNER JOIN (
            SELECT seat_no, MAX(timestamp) as max_timestamp 
            FROM bookings 
            GROUP BY seat_no
        ) b2 ON b1.seat_no = b2.seat_no AND b1.timestamp = b2.max_timestamp
    """)
    all_bookings = cursor.fetchall()
    
   
    seat_status = {}
    for i in range(1, 21):
        seat_status[f'1F-{i}'] = 'available'
        seat_status[f'2F-{i}'] = 'available'
    for i in range(1, 5):
        seat_status[f'CF-{i}'] = 'available'
    
   
    for booking in all_bookings:
        seat_status[booking['seat_no']] = booking['status']
    
    conn.close()
    
    return render_template('visualmap.html', 
                         user_id=session['user_id'],
                         seat_status=seat_status, today_date=today_date)


@app.route('/notification')
def notification():
    if 'user_id' not in session:
        flash("Please login first.")
        return redirect('/login')

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute('''
        SELECT seat_no, status, timing, timestamp 
        FROM bookings 
        WHERE user_id = ?
        ORDER BY timestamp DESC
    ''', (session['user_id'],))
    bookings = cur.fetchall()
    conn.close()
    
    return render_template('notification.html', bookings=bookings)

from flask import flash, redirect, url_for, session


from datetime import datetime, date

@app.route('/book-seat', methods=['POST'])
def book_seat():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    seat_no = request.form.get('seat_no')
    shift = request.form.get('shift')
    booking_date = request.form.get('date') 

   
    if not seat_no or not shift or not booking_date:
        return jsonify({'error': 'Seat number, shift, and date are required'}), 400

    
    try:
        booking_date_obj = datetime.strptime(booking_date, "%Y-%m-%d").date()
    except ValueError:
        return jsonify({'error': 'Invalid date format'}), 400

    
    if booking_date_obj < date.today():
        return jsonify({'error': 'Cannot book for past dates'}), 400

   
    shift_timings = {
        'morning': '09:00 AM to 01:00 PM',
        'afternoon': '01:30 PM to 05:30 PM',
        'evening': '06:00 PM to 09:30 PM'
    }
    timing = shift_timings.get(shift, 'Unknown')

    conn = get_db_connection()
    try:
        cur = conn.cursor()

      
        cur.execute("""
            SELECT id FROM bookings 
            WHERE user_id = ? AND shift = ? AND booking_date = ? 
            AND status IN ('approved', 'pending')
            LIMIT 1
        """, (session['user_id'], shift, booking_date))
        existing_booking = cur.fetchone()

        if existing_booking:
            return jsonify({'error': 'You already have a booking for this shift on this date'}), 400


        cur.execute("""
            SELECT status FROM bookings 
            WHERE seat_no = ? AND booking_date = ?
            ORDER BY timestamp DESC 
            LIMIT 1
        """, (seat_no, booking_date))
        latest_booking = cur.fetchone()

        if latest_booking and latest_booking['status'] in ['approved', 'blocked']:
            return jsonify({'error': 'Seat is already booked or blocked for this date'}), 400

        
        conn.execute("""
            INSERT INTO bookings (user_id, seat_no, status, timing, timestamp, shift, booking_date)
            VALUES (?, ?, 'pending', ?, ?, ?, ?)
        """, (
            session['user_id'], 
            seat_no, 
            timing, 
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'), 
            shift, 
            booking_date_obj.strftime('%Y-%m-%d')
        ))

        conn.commit()
        return jsonify({'success': True, 'message': 'Seat booking request submitted'})

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

@app.before_request
def auto_reset_old_bookings():
    conn = get_db_connection()
    try:
        today = date.today().strftime("%Y-%m-%d")
        conn.execute("""
            UPDATE bookings
            SET status = 'expired'
            WHERE booking_date < ? AND status != 'expired'
        """, (today,))
        conn.commit()
    finally:
        conn.close()


@app.route('/get-seat-details')
def get_seat_details():
    if 'user_id' not in session:
        return jsonify({'error': 'Not authenticated'}), 401

    seat_no = request.args.get('seat_no')
    if not seat_no:
        return jsonify({'error': 'Seat number required'}), 400

    conn = get_db_connection()
    cur = conn.cursor()

    cur.execute("""
        SELECT status 
        FROM bookings 
        WHERE seat_no = ? 
        ORDER BY timestamp DESC 
        LIMIT 1
    """, (seat_no,))
    booking = cur.fetchone()

    status = "Available"  
    if booking:
        db_status = booking['status']
        if db_status == 'approved':
            status = 'Booked'
        elif db_status == 'pending':
            status = 'Pending Approval'
        elif db_status == 'blocked':
            status = 'Blocked'
        elif db_status == 'rejected':
            status = 'Available'
        elif db_status == 'expired':
            status = 'Expired'

    conn.close()

    return jsonify({
        'seat_no': seat_no,
        'status': status
    })




@app.route('/bookings')
def book():
    return render_template('visualmap.html')
@app.route('/admin')
def admin_page():
    if session.get('user') == 'admin':
        conn = get_db_connection()
        cursor = conn.cursor()
        

        cursor.execute("SELECT seat_no, status FROM bookings")
        all_bookings = cursor.fetchall()
        
        
        seat_status = {}
        for i in range(1, 21):
            seat_status[f'1F-{i}'] = 'available'
            seat_status[f'2F-{i}'] = 'available'
        for i in range(1, 5):
            seat_status[f'CF-{i}'] = 'available'
        
        
        for booking in all_bookings:
            seat_status[booking['seat_no']] = booking['status']

        
       
        cursor.execute('''
            SELECT bookings.id, users.fullname, users.email, users.employee_id, 
                   bookings.seat_no, bookings.status, bookings.timing, bookings.timestamp
            FROM bookings
            JOIN users ON bookings.user_id = users.id
            WHERE bookings.status = 'pending'
            ORDER BY bookings.timestamp DESC
        ''')
        pending_bookings = cursor.fetchall()
        
        
        cursor.execute('''
            SELECT bookings.id, users.fullname, users.email, users.employee_id, 
                   bookings.seat_no, bookings.status, bookings.timing, bookings.timestamp
            FROM bookings
            JOIN users ON bookings.user_id = users.id
            WHERE bookings.status = 'approved'
            ORDER BY bookings.timestamp DESC
        ''')
        approved_bookings = cursor.fetchall()
        
        conn.close()
        
        return render_template('admin.html', 
                            seat_status=seat_status,
                            pending_bookings=pending_bookings,
                            approved_bookings=approved_bookings)
    return redirect('/login')

@app.route('/update_booking/<int:booking_id>/<string:action>', methods=['POST'])
def update_booking(booking_id, action):
    if action not in ['approved', 'rejected']:
        flash("Invalid action.", "error")
        return redirect('/admin')

    if session.get('user') != 'admin':
        flash("Admin access required.", "error")
        return redirect('/login')

    conn = get_db_connection()
    
    try:
       
        cur = conn.cursor()
        cur.execute('SELECT seat_no, user_id FROM bookings WHERE id = ?', (booking_id,))
        booking = cur.fetchone()
        seat_no = booking['seat_no']
        user_id = booking['user_id']

        
        conn.execute(
            'UPDATE bookings SET status = ? WHERE id = ?',
            (action, booking_id)
        )
        
        
        if action == 'rejected':
          conn.execute("""
               INSERT INTO bookings (user_id, seat_no, status, timestamp)
               VALUES (?, ?, 'rejected', ?)
                """, (user_id, seat_no, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        flash(f"Seat {seat_no} has been {action}.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error updating booking: {str(e)}", "error")
    finally:
        conn.close()
    
    return redirect('/admin')

@app.route('/block-seat', methods=['POST'])
def block_seat():
    if 'user_id' not in session or session.get('user') != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403

    seat_no = request.form.get('seat_no')
    print(f"Attempting to block seat: {seat_no}")  

    if not seat_no:
        return jsonify({'error': 'Seat number required'}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor()
        cur.execute("SELECT status FROM bookings WHERE seat_no = ? ORDER BY timestamp DESC LIMIT 1", (seat_no,))
        seat = cur.fetchone()

       
        if seat and seat['status'] in ['blocked', 'approved']:
            return jsonify({'error': 'Seat is already blocked or booked'}), 400

        
        cur.execute("""
            INSERT INTO bookings (seat_no, status, timestamp)
            VALUES (?, 'blocked', ?)
        """, (seat_no, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
        
        conn.commit()
        return jsonify({'success': True, 'message': 'Seat blocked successfully'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()
@app.route('/unblock-seat', methods=['POST'])
def unblock_seat():
    if 'user_id' not in session or session.get('user') != 'admin':
        return jsonify({'error': 'Admin authentication required'}), 403

    seat_no = request.form.get('seat_no')

    if not seat_no:
        return jsonify({'error': 'Seat number required'}), 400

    conn = get_db_connection()
    try:
        cur = conn.cursor()

       
        cur.execute("SELECT * FROM bookings WHERE seat_no = ? ORDER BY timestamp DESC LIMIT 1", (seat_no,))
        booking = cur.fetchone()

        if not booking:
            return jsonify({'error': 'Seat not found'}), 404

        if booking['status'] != 'blocked':
            return jsonify({'error': 'Seat is not blocked'}), 400

        
        cur.execute("""
            INSERT INTO bookings (seat_no, status, timestamp)
            VALUES (?, 'rejected', ?)
        """, (seat_no, datetime.now().strftime('%Y-%m-%d %H:%M:%S')))

        conn.commit()
        return jsonify({'success': True, 'message': f'Seat {seat_no} unblocked successfully'}), 200

    except Exception as e:
        conn.rollback()
        return jsonify({'error': str(e)}), 500
    finally:
        conn.close()

if __name__ == '__main__':
    app.run(debug=True)
