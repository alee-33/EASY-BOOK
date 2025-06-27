# ============================== #
# 📦 Imports and Configuration   #
# ============================== #
from flask import Flask, render_template, request, redirect, url_for, session
from werkzeug.utils import secure_filename
from mongoengine import connect
from mongoengine.queryset.visitor import Q
import os

from config import Config
from coll import User, Book, Cart, Shipping, PurchasedBook

app = Flask(__name__)
app.config.from_object(Config)
connect(**app.config["MONGODB_SETTINGS"])
os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)

# ============================ #
# 🧰 Helper Function            #
# ============================ #
def allowed_file(filename):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in app.config["ALLOWED_EXTENSIONS"]

# ============================ #
# 🏠 Home Route                 #
# ============================ #
@app.route("/")
def home():
    return render_template("home.html")

# ============================ #
# 👤 User Signup/Login Routes   #
# ============================ #
@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        if User.objects(email=email).first():
            return "User already exists."
        user = User(email=email, password=password)
        user.save()
        session["user_id"] = str(user.id)
        session["user_email"] = user.email
        return redirect(url_for("shop"))
    return render_template("signup.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        user = User.objects(email=email, password=password, is_admin__ne=True).first()
        if user:
            session["user_id"] = str(user.id)
            session["user_email"] = user.email
            return redirect(url_for("shop"))
        return "Invalid credentials."
    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

# ============================ #
# 👑 Admin Signup/Login Routes #
# ============================ #
@app.route("/admin/signup", methods=["GET", "POST"])
def admin_signup():
    existing_admin = User.objects(is_admin=True).first()
    if existing_admin:
        return redirect(url_for("admin_login"))  

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        
        if User.objects(is_admin=True).first():
            return "❌ Admin already exists."

        admin = User(email=email, password=password, is_admin=True)
        admin.save()
        return redirect(url_for("admin_login"))
    
    return render_template("admin_signup.html")


@app.route("/admin/login", methods=["GET", "POST"])
def admin_login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]
        admin = User.objects(email=email, password=password, is_admin=True).first()
        if admin:
            session["admin_id"] = str(admin.id)
            session["admin_email"] = admin.email
            return redirect(url_for("admin_dashboard"))
        return "Invalid admin credentials."
    return render_template("admin_login.html")

@app.route("/admin/dashboard")
def admin_dashboard():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    return render_template("admin_dashboard.html")

# ============================ #
# 📚 Admin Book Management      #
# ============================ #
@app.route("/admin/add_book", methods=["GET", "POST"])
def add_book():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        try:
            img = request.files.get("image")
            filename = None
            if img and allowed_file(img.filename):
                filename = secure_filename(img.filename)
                img.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            book = Book(
                iban=request.form["iban"],
                name=request.form["name"],
                author=request.form["author"],
                price=int(request.form["price"]),
                quantity=int(request.form["quantity"]),
                image=filename
            )
            book.save()
            return "✅ Book Added!"
        except Exception as e:
            return f"❌ Error: {str(e)}"
    return render_template("add_book.html")

@app.route("/admin/update_book", methods=["GET", "POST"])
def update_book():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        iban = request.form["iban"]
        book = Book.objects(iban=iban).first()
        if not book:
            return "❌ Book Not Found"
        book.name = request.form.get("name", book.name)
        book.author = request.form.get("author", book.author)
        book.price = int(request.form.get("price", book.price))
        book.quantity = int(request.form.get("quantity", book.quantity))
        img = request.files.get("image")
        if img and allowed_file(img.filename):
            filename = secure_filename(img.filename)
            img.save(os.path.join(app.config["UPLOAD_FOLDER"], filename))
            book.image = filename
        book.save()
        return "✅ Book Updated!"
    return render_template("update_book.html")

@app.route("/admin/delete_book", methods=["GET", "POST"])
def delete_book():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    if request.method == "POST":
        iban = request.form["iban"]
        book = Book.objects(iban=iban).first()
        if book:
            book.delete()
            return "🗑️ Book Deleted"
        return "❌ Book Not Found"
    return render_template("delete_book.html")

@app.route("/admin/show_books", methods=["GET", "POST"])
def show_books_admin():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    query = request.form.get("query", "")
    books = Book.objects(Q(name__icontains=query) | Q(author__icontains=query) | Q(iban__icontains=query)) if query else Book.objects()
    return render_template("show_books_admin.html", books=books)

# ============================ #
# 🛍️ User Book Shop Route      #
# ============================ #
@app.route("/shop", methods=["GET", "POST"])
def shop():
    if "user_id" not in session:
        return redirect(url_for("login"))
    query = request.form.get("q", "")
    books = Book.objects(Q(name__icontains=query) | Q(author__icontains=query) | Q(iban__icontains=query)) if query else Book.objects()
    return render_template("show_books_user.html", books=books)

# ============================ #
# 🛒 Cart Management Routes     #
# ============================ #
@app.route("/add_to_cart/<book_id>", methods=["POST"])
def add_to_cart(book_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.objects(id=session["user_id"]).first()
    book = Book.objects(id=book_id).first()
    if not book or book.quantity == 0:
        return "Book not available"
    item = Cart.objects(user=user, book=book).first()
    if item:
        if item.quantity < book.quantity:
            item.quantity += 1
            item.save()
        else:
            return "Max quantity reached."
    else:
        Cart(user=user, book=book, quantity=1).save()
    return redirect(url_for("shop"))

@app.route("/view_cart")
def view_cart():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.objects(id=session["user_id"]).first()
    cart_items = Cart.objects(user=user)
    return render_template("view_cart.html", cart_items=cart_items)

@app.route("/update_cart_quantity", methods=["POST"])
def update_cart_quantity():
    if "user_id" not in session:
        return redirect(url_for("login"))
    cart_id = request.form["cart_id"]
    action = request.form["action"]
    cart_item = Cart.objects(id=cart_id).first()
    if cart_item and str(cart_item.user.id) == session["user_id"]:
        if action == "increase" and cart_item.quantity < cart_item.book.quantity:
            cart_item.quantity += 1
        elif action == "decrease" and cart_item.quantity > 1:
            cart_item.quantity -= 1
        cart_item.save()
    return redirect(url_for("view_cart"))

@app.route("/remove_from_cart/<cart_id>", methods=["POST"])
def remove_from_cart(cart_id):
    if "user_id" not in session:
        return redirect(url_for("login"))
    Cart.objects(id=cart_id, user=session["user_id"]).delete()
    return redirect(url_for("view_cart"))

# ============================ #
# 💳 Checkout and Purchase      #
# ============================ #
@app.route("/checkout", methods=["GET", "POST"])
def checkout():
    if "user_id" not in session:
        return redirect(url_for("login"))
    
    user = User.objects(id=session["user_id"]).first()
    cart_items = Cart.objects(user=user)

    if request.method == "POST":
        name = request.form["name"]
        address = request.form["address"]
        mobile = request.form["mobile"]

        purchased_books = [
            PurchasedBook(
                name=item.book.name,
                price=item.book.price,
                quantity=item.quantity
            )
            for item in cart_items
        ]

        Shipping(
            user=user,
            name=name,
            address=address,
            mobile=mobile,
            books=purchased_books
        ).save()

        for item in cart_items:
            if item.book.quantity >= item.quantity:
                item.book.quantity -= item.quantity
                item.book.save()

        cart_items.delete()
        total = sum(p.price * p.quantity for p in purchased_books)

        return render_template("order_summary.html", total=total, user=user)

    total = sum(item.book.price * item.quantity for item in cart_items)
    return render_template("checkout.html", cart_items=cart_items, total=total, user=user)

# ============================ #
# 📜 Order History Page         #
# ============================ #
@app.route("/history")
def view_history():
    if "user_id" not in session:
        return redirect(url_for("login"))
    user = User.objects(id=session["user_id"]).first()
    orders = Shipping.objects(user=user)
    book_names = {p.name for order in orders for p in order.books}
    books_lookup = {b.name: b for b in Book.objects(name__in=list(book_names))}
    return render_template("history.html", history=orders, books_lookup=books_lookup)



# ============================ #
# 📜 Admin View Sold History    #
# ============================ #
@app.route("/admin/view_history")
def admin_view_history():
    if "admin_id" not in session:
        return redirect(url_for("admin_login"))
    orders = Shipping.objects()
    book_names = {p.name for order in orders for p in order.books}
    books_lookup = {b.name: b for b in Book.objects(name__in=list(book_names))}
    return render_template("admin_history.html", history=orders, books_lookup=books_lookup)



# ============================ #
# 🚀 Run the Flask App          #
# ============================ #
if __name__ == "__main__":
    app.run(debug=True)
