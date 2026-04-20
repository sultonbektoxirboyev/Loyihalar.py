import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import hashlib
import os
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from PIL import Image, ImageTk
from io import BytesIO

DB_NAME = "advanced_bookstore.db"

class LoginWindow:
    def __init__(self, root, callback):
        self.root = root
        self.callback = callback
        self.root.title("🔐 Kirish")
        self.root.geometry("400x350")
        self.root.configure(bg='#2c3e50')
        self.root.resizable(False, False)
        
        self.create_widgets()
        self.setup_database()
    
    def create_widgets(self):
        # Logo/Sarlavha
        tk.Label(self.root, text="📚 KITOB DO'KONI", 
                font=('Arial', 24, 'bold'), bg='#2c3e50', fg='white').pack(pady=20)
        
        frame = tk.Frame(self.root, bg='white', padx=30, pady=30)
        frame.pack(pady=10)
        
        # Username
        tk.Label(frame, text="Foydalanuvchi nomi:", 
                font=('Arial', 11), bg='white').pack(anchor='w', pady=5)
        self.username_entry = tk.Entry(frame, font=('Arial', 12), width=25)
        self.username_entry.pack(pady=5)
        
        # Password
        tk.Label(frame, text="Parol:", 
                font=('Arial', 11), bg='white').pack(anchor='w', pady=5)
        self.password_entry = tk.Entry(frame, font=('Arial', 12), width=25, show='*')
        self.password_entry.pack(pady=5)
        
        # Tugmalar
        tk.Button(frame, text="Kirish", command=self.login, 
                 bg='#27ae60', fg='white', font=('Arial', 12, 'bold'),
                 width=20, pady=8).pack(pady=15)
        
        tk.Button(frame, text="Ro'yxatdan o'tish", command=self.register, 
                 bg='#3498db', fg='white', font=('Arial', 11),
                 width=20, pady=5).pack(pady=5)
    
    def setup_database(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL,
                email TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS orders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                total_amount REAL,
                order_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                status TEXT DEFAULT 'completed',
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS order_items (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                order_id INTEGER,
                book_id INTEGER,
                title TEXT,
                quantity INTEGER,
                price REAL,
                FOREIGN KEY (order_id) REFERENCES orders(id),
                FOREIGN KEY (book_id) REFERENCES books(id)
            )
        ''')
        conn.commit()
        conn.close()
    
    def hash_password(self, password):
        return hashlib.sha256(password.encode()).hexdigest()
    
    def register(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Xatolik", "Barcha maydonlarni to'ldiring!")
            return
        
        try:
            conn = sqlite3.connect(DB_NAME)
            cursor = conn.cursor()
            hashed_pw = self.hash_password(password)
            cursor.execute("INSERT INTO users (username, password) VALUES (?, ?)", 
                          (username, hashed_pw))
            conn.commit()
            conn.close()
            messagebox.showinfo("Muvaffaqiyatli bo'ldi", "Ro'yxatdan o'tdingiz!")
        except sqlite3.IntegrityError:
            messagebox.showerror("Xatolik", "Bu foydalanuvchi nomi band!")
    
    def login(self):
        username = self.username_entry.get().strip()
        password = self.password_entry.get().strip()
        
        if not username or not password:
            messagebox.showerror("Xatolik", "Foydalanuvchi nomi va parolni kiriting!")
            return
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        hashed_pw = self.hash_password(password)
        cursor.execute("SELECT id, username FROM users WHERE username=? AND password=?", 
                      (username, hashed_pw))
        user = cursor.fetchone()
        conn.close()
        
        if user:
            self.root.destroy()
            self.callback(user)  # user_id va username
        else:
            messagebox.showerror("Xatolik", "Foydalanuvchi nomi yoki parol noto'g'ri!")

class AdvancedBookStore:
    def __init__(self, root, user):
        self.root = root
        self.user_id = user[0]
        self.username = user[1]
        self.root.title(f"📚 Online Kitob Do'koni - {self.username}")
        self.root.geometry("1200x750")
        self.root.configure(bg='#f0f0f0')
        
        self.cart = []
        self.current_user_books = []  # User kitoblari uchun
        
        self.create_widgets()
        self.setup_database()
        self.refresh_books()
        self.update_user_stats()
    
    def create_widgets(self):
        # Yuqori panel
        top_frame = tk.Frame(self.root, bg='#2c3e50', height=70)
        top_frame.pack(fill='x')
        top_frame.pack_propagate(False)
        
        tk.Label(top_frame, text=f"📚 Xush kelibsiz, {self.username}!", 
                font=('Arial', 20, 'bold'), bg='#2c3e50', fg='white').pack(side='left', padx=20, pady=15)
        
        tk.Button(top_frame, text="📊 Statistika", command=self.show_statistics,
                 bg='#9b59b6', fg='white', font=('Arial', 11, 'bold'),
                 padx=15, pady=8).pack(side='right', padx=5)
        
        tk.Button(top_frame, text="📦 Buyurtmalarim", command=self.show_order_history,
                 bg='#e67e22', fg='white', font=('Arial', 11, 'bold'),
                 padx=15, pady=8).pack(side='right', padx=5)
        
        tk.Button(top_frame, text="🚪 Chiqish", command=self.logout,
                 bg='#c0392b', fg='white', font=('Arial', 11),
                 padx=15, pady=8).pack(side='right', padx=5)
        
        # Asosiy konteyner
        main_container = tk.Frame(self.root, bg='#f0f0f0')
        main_container.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Qidiruv paneli
        search_frame = tk.Frame(main_container, bg='white', relief='raised', borderwidth=1)
        search_frame.pack(fill='x', pady=(0, 10))
        
        tk.Label(search_frame, text="🔍 Qidiruv:", 
                font=('Arial', 12, 'bold'), bg='white').pack(side='left', padx=10, pady=8)
        
        self.search_entry = tk.Entry(search_frame, font=('Arial', 12), width=40)
        self.search_entry.pack(side='left', padx=10, pady=8)
        self.search_entry.bind('<Return>', lambda e: self.search_books())
        
        tk.Button(search_frame, text="Qidirish", command=self.search_books,
                 bg='#3498db', fg='white', font=('Arial', 11),
                 padx=15).pack(side='left', padx=5)
        
        tk.Button(search_frame, text="Tozalash", command=self.clear_search,
                 bg='#95a5a6', fg='white', font=('Arial', 11),
                 padx=15).pack(side='left', padx=5)
        
        # Chap tomon - Kitoblar
        left_frame = tk.Frame(main_container, bg='white', relief='raised', borderwidth=2)
        left_frame.pack(side='left', fill='both', expand=True, padx=(0, 5))
        
        tk.Label(left_frame, text="📖 Kitoblar", 
                font=('Arial', 14, 'bold'), bg='white').pack(pady=10)
        
        # Kitoblar jadvali
        columns = ('ID', 'Muqova', 'Nomi', 'Muallif', 'Narx', 'Qoldiq')
        self.book_tree = ttk.Treeview(left_frame, columns=columns, show='headings', height=18)
        
        self.book_tree.heading('ID', text='ID')
        self.book_tree.heading('Muqova', text='Muqova')
        self.book_tree.heading('Nomi', text='Nomi')
        self.book_tree.heading('Muallif', text='Muallif')
        self.book_tree.heading('Narx', text='Narx')
        self.book_tree.heading('Qoldiq', text='Qoldiq')
        
        self.book_tree.column('ID', width=40)
        self.book_tree.column('Muqova', width=80)
        self.book_tree.column('Nomi', width=200)
        self.book_tree.column('Muallif', width=180)
        self.book_tree.column('Narx', width=100)
        self.book_tree.column('Qoldiq', width=70)
        
        # Scrollbar
        scrollbar = ttk.Scrollbar(left_frame, orient='vertical', command=self.book_tree.yview)
        self.book_tree.configure(yscrollcommand=scrollbar.set)
        
        self.book_tree.pack(side='left', fill='both', expand=True, padx=5, pady=5)
        scrollbar.pack(side='right', fill='y')
        
        # Tugmalar
        btn_frame = tk.Frame(left_frame, bg='white')
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        tk.Button(btn_frame, text="🛒 Savatchaga qo'shish", 
                 command=self.add_to_cart, bg='#27ae60', fg='white',
                 font=('Arial', 11, 'bold'), padx=10, pady=8).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="🔄 Yangilash", 
                 command=self.refresh_books, bg='#3498db', fg='white',
                 font=('Arial', 11), padx=10, pady=8).pack(side='left', padx=5)
        
        tk.Button(btn_frame, text="📷 Muqova yuklash", 
                 command=self.upload_cover, bg='#16a085', fg='white',
                 font=('Arial', 10), padx=10, pady=8).pack(side='left', padx=5)
        
        # O'ng tomon - Savatcha
        right_frame = tk.Frame(main_container, bg='white', relief='raised', borderwidth=2, width=350)
        right_frame.pack(side='right', fill='both', padx=(5, 0))
        right_frame.pack_propagate(False)
        
        tk.Label(right_frame, text="🛒 Savatcha", 
                font=('Arial', 14, 'bold'), bg='white').pack(pady=10)
        
        # Savatcha ro'yxati
        self.cart_frame = tk.Frame(right_frame, bg='white')
        self.cart_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        self.cart_scrollbar = ttk.Scrollbar(self.cart_frame)
        self.cart_scrollbar.pack(side='right', fill='y')
        
        self.cart_listbox = tk.Listbox(self.cart_frame, font=('Arial', 10), 
                                       height=12, yscrollcommand=self.cart_scrollbar.set)
        self.cart_listbox.pack(side='left', fill='both', expand=True)
        self.cart_scrollbar.config(command=self.cart_listbox.yview)
        
        self.cart_listbox.bind('<<ListboxSelect>>', self.on_cart_select)
        
        # Jami summa
        self.total_label = tk.Label(right_frame, text="Jami: 0 so'm", 
                                   font=('Arial', 14, 'bold'), bg='#ecf0f1', fg='#e74c3c',
                                   pady=10)
        self.total_label.pack(fill='x', padx=10)
        
        # Foydalanuvchi statistikasi
        self.user_stats_label = tk.Label(right_frame, text="", 
                                        font=('Arial', 9), bg='white', fg='#7f8c8d')
        self.user_stats_label.pack(pady=5)
        
        # Savatcha tugmalari
        cart_btn_frame = tk.Frame(right_frame, bg='white')
        cart_btn_frame.pack(fill='x', padx=10, pady=10)
        
        tk.Button(cart_btn_frame, text="🗑️ O'chirish", 
                 command=self.remove_from_cart, bg='#e74c3c', fg='white',
                 font=('Arial', 10), padx=10, pady=5).pack(side='left', padx=2, pady=5)
        
        tk.Button(cart_btn_frame, text="➕ Sonini oshirish", 
                 command=self.increase_qty, bg='#f39c12', fg='white',
                 font=('Arial', 9), padx=8, pady=5).pack(side='left', padx=2, pady=5)
        
        tk.Button(cart_btn_frame, text="➖ Sonini kamaytirish", 
                 command=self.decrease_qty, bg='#95a5a6', fg='white',
                 font=('Arial', 9), padx=8, pady=5).pack(side='left', padx=2, pady=5)
        
        tk.Button(right_frame, text="✅ Buyurtma berish", 
                 command=self.checkout, bg='#27ae60', fg='white',
                 font=('Arial', 12, 'bold'), padx=20, pady=10).pack(pady=10)
        
        # Status bar
        self.status_bar = tk.Label(self.root, text="Tayyor", bd=1, relief='sunken', anchor='w')
        self.status_bar.pack(side='bottom', fill='x')
    
    def setup_database(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS books (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                author TEXT NOT NULL,
                price REAL NOT NULL,
                stock INTEGER NOT NULL DEFAULT 10,
                cover_path TEXT
            )
        ''')
        
        # Namuna ma'lumotlar
        cursor.execute("SELECT COUNT(*) FROM books")
        if cursor.fetchone()[0] == 0:
            samples = [
                ("Python Dasturlash", "Mark Lutz", 45000, 15, None),
                ("Algoritmlar", "Thomas Cormen", 120000, 8, None),
                ("Sun'iy Intellekt", "Stuart Russell", 95000, 12, None),
                ("Ma'lumotlar Tuzilmasi", "Robert Sedgewick", 85000, 5, None),
                ("Web Dasturlash", "Jon Duckett", 65000, 10, None),
                ("JavaScript", "Douglas Crockford", 55000, 20, None),
                ("Java", "Herbert Schildt", 75000, 12, None),
                ("C++", "Bjarne Stroustrup", 90000, 7, None)
            ]
            cursor.executemany("INSERT INTO books (title, author, price, stock, cover_path) VALUES (?, ?, ?, ?, ?)", samples)
            conn.commit()
        
        conn.close()
    
    def refresh_books(self):
        for item in self.book_tree.get_children():
            self.book_tree.delete(item)
        
        conn = sqlite3.connect(DB_NAME)
        books = conn.execute("SELECT id, title, author, price, stock, cover_path FROM books").fetchall()
        conn.close()
        
        for book in books:
            cover_text = "📷" if book[5] else "❌"
            values = (book[0], cover_text, book[1], book[2], f"{book[3]:,.0f}", book[4])
            self.book_tree.insert('', 'end', values=values)
        
        self.status_bar.config(text=f"Jami kitoblar: {len(books)}")
    
    def search_books(self):
        query = self.search_entry.get().strip().lower()
        if not query:
            self.refresh_books()
            return
        
        for item in self.book_tree.get_children():
            self.book_tree.delete(item)
        
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT id, title, author, price, stock, cover_path 
            FROM books 
            WHERE LOWER(title) LIKE ? OR LOWER(author) LIKE ?
        """, (f'%{query}%', f'%{query}%'))
        books = cursor.fetchall()
        conn.close()
        
        for book in books:
            cover_text = "📷" if book[5] else "❌"
            values = (book[0], cover_text, book[1], book[2], f"{book[3]:,.0f}", book[4])
            self.book_tree.insert('', 'end', values=values)
        
        self.status_bar.config(text=f"Topildi: {len(books)} ta kitob")
    
    def clear_search(self):
        self.search_entry.delete(0, tk.END)
        self.refresh_books()
    
    def upload_cover(self):
        selected = self.book_tree.selection()
        if not selected:
            messagebox.showwarning("Ogohlantirish", "Iltimos, kitob tanlang!")
            return
        
        item = self.book_tree.item(selected[0])
        book_id = item['values'][0]
        
        file_path = filedialog.askopenfilename(
            title="Muqova tanlang",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif")]
        )
        
        if file_path:
            # Rasmni saqlash uchun papka yaratish
            os.makedirs("book_covers", exist_ok=True)
            save_path = os.path.join("book_covers", f"book_{book_id}.jpg")
            
            # Rasmni o'lchamini o'zgartirish va saqlash
            img = Image.open(file_path)
            img.thumbnail((200, 300))
            img.save(save_path, "JPEG")
            
            # Ma'lumotlar bazasiga yo'lni saqlash
            conn = sqlite3.connect(DB_NAME)
            conn.execute("UPDATE books SET cover_path = ? WHERE id = ?", (save_path, book_id))
            conn.commit()
            conn.close()
            
            messagebox.showinfo("Muvaffaqiyatli", "Muqova yuklandi!")
            self.refresh_books()
    
    def add_to_cart(self):
        selected = self.book_tree.selection()
        if not selected:
            messagebox.showwarning("Ogohlantirish", "Iltimos, kitob tanlang!")
            return
        
        item = self.book_tree.item(selected[0])
        book_id, _, title, author, price, stock = item['values']
        price = float(price.replace(',', ''))
        
        for cart_item in self.cart:
            if cart_item['id'] == book_id:
                if cart_item['qty'] < stock:
                    cart_item['qty'] += 1
                    self.update_cart_display()
                    messagebox.showinfo("Muvaffaqiyatli", f"{title} soni oshirildi!")
                else:
                    messagebox.showerror("Xatolik", "Omborda yetarli zaxira yo'q!")
                return
        
        self.cart.append({
            'id': book_id,
            'title': title,
            'author': author,
            'price': price,
            'qty': 1,
            'stock': stock
        })
        
        self.update_cart_display()
        messagebox.showinfo("Muvaffaqiyatli", f"{title} savatchaga qo'shildi!")
    
    def update_cart_display(self):
        self.cart_listbox.delete(0, tk.END)
        total = 0
        
        for i, item in enumerate(self.cart):
            subtotal = item['price'] * item['qty']
            total += subtotal
            self.cart_listbox.insert(tk.END, 
                f"{i+1}. {item['title']}\n   x{item['qty']} - {subtotal:,.0f} so'm")
        
        self.total_label.config(text=f"Jami: {total:,.0f} so'm")
    
    def on_cart_select(self, event):
        pass  # Kelajakda tanlangan elementni ko'rsatish uchun
    
    def remove_from_cart(self):
        selection = self.cart_listbox.curselection()
        if not selection:
            messagebox.showwarning("Ogohlantirish", "Iltimos, element tanlang!")
            return
        
        index = selection[0]
        removed = self.cart.pop(index)
        self.update_cart_display()
        messagebox.showinfo("O'chirildi", f"{removed['title']} o'chirildi!")
    
    def increase_qty(self):
        selection = self.cart_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        cart_item = self.cart[index]
        
        if cart_item['qty'] < cart_item['stock']:
            cart_item['qty'] += 1
            self.update_cart_display()
        else:
            messagebox.showerror("Xatolik", "Maksimal miqdorga yetdingiz!")
    
    def decrease_qty(self):
        selection = self.cart_listbox.curselection()
        if not selection:
            return
        
        index = selection[0]
        cart_item = self.cart[index]
        
        if cart_item['qty'] > 1:
            cart_item['qty'] -= 1
            self.update_cart_display()
        else:
            if messagebox.askyesno("Tasdiqlash", "Savatchadan o'chirilsinmi?"):
                self.remove_from_cart()
    
    def checkout(self):
        if not self.cart:
            messagebox.showwarning("Ogohlantirish", "Savatcha bo'sh!")
            return
        
        total = sum(item['price'] * item['qty'] for item in self.cart)
        
        if messagebox.askyesno("Tasdiqlash", 
                              f"Buyurtma berishni tasdiqlaysizmi?\n\nJami summa: {total:,.0f} so'm"):
            conn = sqlite3.connect(DB_NAME)
            cur = conn.cursor()
            
            # Buyurtma yaratish
            cur.execute("INSERT INTO orders (user_id, total_amount) VALUES (?, ?)", 
                       (self.user_id, total))
            order_id = cur.lastrowid
            
            # Buyurtma elementlarini saqlash
            for item in self.cart:
                cur.execute("""
                    INSERT INTO order_items (order_id, book_id, title, quantity, price)
                    VALUES (?, ?, ?, ?, ?)
                """, (order_id, item['id'], item['title'], item['qty'], item['price']))
                
                # Omborni yangilash
                cur.execute("UPDATE books SET stock = stock - ? WHERE id = ?", 
                           (item['qty'], item['id']))
            
            conn.commit()
            conn.close()
            
            self.cart.clear()
            self.update_cart_display()
            self.refresh_books()
            self.update_user_stats()
            
            messagebox.showinfo("Muvaffaqiyatli!", "✅ Buyurtma qabul qilindi!\n\nRahmat!")
    
    def show_order_history(self):
        history_window = tk.Toplevel(self.root)
        history_window.title(f"📦 Buyurtmalar tarixi - {self.username}")
        history_window.geometry("800x600")
        
        # Sarlavha
        tk.Label(history_window, text="📦 Mening Buyurtmalarim", 
                font=('Arial', 18, 'bold')).pack(pady=10)
        
        # Jadval
        columns = ('ID', 'Sana', 'Summa', 'Status')
        tree = ttk.Treeview(history_window, columns=columns, show='headings', height=15)
        
        for col in columns:
            tree.heading(col, text=col)
            tree.column(col, width=150)
        
        tree.pack(fill='both', expand=True, padx=10, pady=10)
        
        # Ma'lumotlarni yuklash
        conn = sqlite3.connect(DB_NAME)
        orders = conn.execute("""
            SELECT id, order_date, total_amount, status 
            FROM orders 
            WHERE user_id = ?
            ORDER BY order_date DESC
        """, (self.user_id,)).fetchall()
        conn.close()
        
        for order in orders:
            tree.insert('', 'end', values=(
                order[0], 
                order[1], 
                f"{order[2]:,.0f} so'm", 
                order[3]
            ))
        
        # Tugma
        tk.Button(history_window, text="Yopish", command=history_window.destroy,
                 bg='#95a5a6', fg='white', font=('Arial', 11),
                 padx=20, pady=8).pack(pady=10)
    
    def show_statistics(self):
        stats_window = tk.Toplevel(self.root)
        stats_window.title("📊 Statistika")
        stats_window.geometry("900x700")
        
        # Sarlavha
        tk.Label(stats_window, text="📊 Do'kon Statistikasi", 
                font=('Arial', 18, 'bold')).pack(pady=10)
        
        # Frame for charts
        chart_frame = tk.Frame(stats_window)
        chart_frame.pack(fill='both', expand=True, padx=10, pady=10)
        
        conn = sqlite3.connect(DB_NAME)
        
        # 1. Kitoblar bo'yicha savdo statistikasi
        cursor = conn.execute("""
            SELECT title, SUM(quantity) as total_sold
            FROM order_items
            GROUP BY book_id
            ORDER BY total_sold DESC
            LIMIT 5
        """)
        top_books = cursor.fetchall()
        
        if top_books:
            # Matplotlib grafigi
            fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(10, 4))
            
            # Top kitoblar
            books = [b[0][:15] for b in top_books]
            sales = [b[1] for b in top_books]
            
            ax1.bar(books, sales, color=['#27ae60', '#3498db', '#e67e22', '#9b59b6', '#e74c3c'])
            ax1.set_title('Eng koʻp sotilgan kitoblar')
            ax1.tick_params(axis='x', rotation=45)
            
            # Umumiy savdo
            cursor = conn.execute("SELECT COUNT(*), SUM(total_amount) FROM orders")
            total_orders, total_revenue = cursor.fetchone()
            
            stats_text = f"""
            📊 UMUMIY STATISTIKA:
            
            ✅ Jami buyurtmalar: {total_orders or 0}
            💰 Umumiy daromad: {total_revenue:,.0f} so'm
            📚 Jami kitoblar: {len(self.book_tree.get_children())}
            👤 Foydalanuvchi: {self.username}
            """
            
            ax2.axis('off')
            ax2.text(0.1, 0.5, stats_text, fontsize=12, verticalalignment='center',
                    fontfamily='monospace', bbox=dict(boxstyle="round,pad=0.5", 
                    facecolor="#ecf0f1", alpha=0.8))
            
            plt.tight_layout()
            
            canvas = FigureCanvasTkAgg(fig, master=chart_frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill='both', expand=True)
        
        conn.close()
        
        # Yopish tugmasi
        tk.Button(stats_window, text="Yopish", command=stats_window.destroy,
                 bg='#95a5a6', fg='white', font=('Arial', 11),
                 padx=20, pady=8).pack(pady=10)
    
    def update_user_stats(self):
        conn = sqlite3.connect(DB_NAME)
        cursor = conn.execute("""
            SELECT COUNT(*), SUM(total_amount) 
            FROM orders 
            WHERE user_id = ?
        """, (self.user_id,))
        result = cursor.fetchone()
        conn.close()
        
        orders_count = result[0] or 0
        total_spent = result[1] or 0
        
        stats_text = f"Sizning statistika:\n📦 Buyurtmalar: {orders_count}\n💰 Sarflangan: {total_spent:,.0f} so'm"
        self.user_stats_label.config(text=stats_text)
    
    def logout(self):
        if messagebox.askyesno("Chiqish", "Chiqishni xohlaysizmi?"):
            self.root.destroy()
            main()  # Login oynasini qayta ochish

def main():
    root = tk.Tk()
    # Test uchun vaqtinchalik foydalanuvchi (ID, Foydalanuvchi nomi)
    test_user = (1, "TestFoydalanuvchi")
    app = AdvancedBookStore(root, test_user)
    root.mainloop()
if __name__ == "__main__":
    main()
