from flask import Flask, render_template, redirect, url_for, session, request
import mysql.connector
import os

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY", "foodgo-secret")


def get_db():
    return mysql.connector.connect(
        host=os.getenv("MYSQL_HOST", "localhost"),
        port=int(os.getenv("MYSQL_PORT", "3306")),
        user=os.getenv("MYSQL_USER", "foodgo"),
        password=os.getenv("MYSQL_PASSWORD", "foodgo123"),
        database=os.getenv("MYSQL_DATABASE", "foodgo")
    )


restaurants = [
    {
        "id": 1,
        "name": "Pizza Palace",
        "category": "Pizza • Italian",
        "rating": "4.5",
        "time": "25-30 min",
        "emoji": "🍕",
        "items": [
            {"id": 101, "name": "Margherita Pizza", "price": 249},
            {"id": 102, "name": "Farmhouse Pizza", "price": 329},
            {"id": 103, "name": "Garlic Bread", "price": 149}
        ]
    },
    {
        "id": 2,
        "name": "Burger House",
        "category": "Burgers • Fast Food",
        "rating": "4.3",
        "time": "20-25 min",
        "emoji": "🍔",
        "items": [
            {"id": 201, "name": "Classic Burger", "price": 199},
            {"id": 202, "name": "Cheese Burger", "price": 249},
            {"id": 203, "name": "French Fries", "price": 129}
        ]
    },
    {
        "id": 3,
        "name": "Spice Garden",
        "category": "Indian • North Indian",
        "rating": "4.6",
        "time": "30-35 min",
        "emoji": "🍛",
        "items": [
            {"id": 301, "name": "Paneer Butter Masala", "price": 289},
            {"id": 302, "name": "Dal Makhani", "price": 219},
            {"id": 303, "name": "Butter Naan", "price": 59}
        ]
    }
]


def all_items():
    return {
        item["id"]: {
            **item,
            "restaurant": restaurant["name"]
        }
        for restaurant in restaurants
        for item in restaurant["items"]
    }


@app.route("/")
def index():
    return render_template(
        "index.html",
        restaurants=restaurants,
        cart_count=len(session.get("cart", []))
    )


@app.route("/restaurant/<int:restaurant_id>")
def restaurant(restaurant_id):
    restaurant_data = next(
        (r for r in restaurants if r["id"] == restaurant_id),
        None
    )

    if not restaurant_data:
        return "Restaurant not found", 404

    return render_template(
        "restaurant.html",
        restaurant=restaurant_data,
        cart_count=len(session.get("cart", []))
    )


@app.post("/cart/add/<int:item_id>")
def add_to_cart(item_id):
    if item_id in all_items():
        cart = session.get("cart", [])
        cart.append(item_id)
        session["cart"] = cart

    return redirect(request.referrer or url_for("index"))


@app.route("/cart")
def cart():
    items = all_items()

    selected_items = [
        items[item_id]
        for item_id in session.get("cart", [])
        if item_id in items
    ]

    total = sum(item["price"] for item in selected_items)

    return render_template(
        "cart.html",
        items=selected_items,
        total=total
    )


@app.post("/cart/clear")
def clear_cart():
    session["cart"] = []
    return redirect(url_for("cart"))


@app.route("/checkout")
def checkout():
    items = all_items()

    selected_items = [
        items[item_id]
        for item_id in session.get("cart", [])
        if item_id in items
    ]

    if not selected_items:
        return redirect(url_for("cart"))

    total = sum(item["price"] for item in selected_items)

    return render_template(
        "checkout.html",
        items=selected_items,
        total=total
    )


@app.post("/order")
def order():
    name = request.form.get("name")
    email = request.form.get("email")
    phone = request.form.get("phone")
    address = request.form.get("address")

    items = all_items()

    selected_items = [
        items[item_id]
        for item_id in session.get("cart", [])
        if item_id in items
    ]

    if not selected_items:
        return redirect(url_for("cart"))

    total = sum(item["price"] for item in selected_items)

    db = get_db()
    cursor = db.cursor()

    cursor.execute(
        """
        INSERT INTO customers (name, email, phone, address)
        VALUES (%s, %s, %s, %s)
        """,
        (name, email, phone, address)
    )

    customer_id = cursor.lastrowid

    cursor.execute(
        """
        INSERT INTO orders (customer_id, restaurant, total)
        VALUES (%s, %s, %s)
        """,
        (
            customer_id,
            selected_items[0]["restaurant"],
            total
        )
    )

    order_id = cursor.lastrowid

    for item in selected_items:
        cursor.execute(
            """
            INSERT INTO order_items
            (order_id, item_name, price)
            VALUES (%s, %s, %s)
            """,
            (
                order_id,
                item["name"],
                item["price"]
            )
        )

    db.commit()

    cursor.close()
    db.close()

    session["cart"] = []

    return render_template(
        "order.html",
        item_count=len(selected_items),
        total=total,
        order_id=order_id,
        customer_name=name
    )


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)