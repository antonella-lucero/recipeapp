from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from dotenv import load_dotenv
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
import os
import requests

load_dotenv()
# Application Setup
app = Flask(__name__)
app = Flask(__name__, static_url_path='/static')
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///recipes.db')
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev')
api_key = os.getenv('SPOONACULAR_API_KEY')
db = SQLAlchemy(app)

# Database Models
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    saved_recipes = db.relationship('SavedRecipe', backref='user', lazy=True)
    cart = db.relationship('Cart', uselist=False, backref='user')

    def __repr__(self):
        return f'<User {self.username}>'

    def set_password(self, password):
        self.password = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password, password)

class SavedRecipe(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(255), nullable=False)
    recipe_id = db.Column(db.Integer, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f'<SavedRecipe {self.title}>'

class Cart(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    cart_items = db.relationship('CartItem', backref='cart', lazy=True)

    def __repr__(self):
        return f'<Cart {self.id} for User {self.user_id}>'

class CartItem(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ingredient_name = db.Column(db.String(255), nullable=False)
    quantity = db.Column(db.Float, nullable=False)
    unit = db.Column(db.String(50), nullable=True)
    recipe_id = db.Column(db.Integer, nullable=False)
    cart_id = db.Column(db.Integer, db.ForeignKey('cart.id'), nullable=False)

    def __repr__(self):
        return f'<CartItem {self.ingredient_name} for Cart {self.cart_id}>'

# Utility Functions
def authenticate(username, password):
    user = User.query.filter_by(username=username).first()
    if user and user.check_password(password):
        return True
    return False

def fetch_recipes(ingredients, number_of_recipes=5):
    url = f'https://api.spoonacular.com/recipes/findByIngredients?apiKey={api_key}&ingredients={ingredients}&number={number_of_recipes}'
    response = requests.get(url)

    print(f'Response status code: {response.status_code}')  
    if response.status_code != 200:
        return []  
    
    recipes = response.json()
    print(f'Number of recipes fetched: {len(recipes)}')  

    for recipe in recipes:
        details_url = f'https://api.spoonacular.com/recipes/{recipe["id"]}/information?apiKey={api_key}'
        try:
            details_response = requests.get(details_url)
        except Exception as e:
            print(f"Failed to get details for recipe {recipe['id']}: {e}")
            continue
            
        print(f'Details response status code: {details_response.status_code}')  

        if details_response.status_code != 200:
            print(f'Failed to fetch details for recipe {recipe["id"]}')  
            continue  

        recipe_details = details_response.json()
        recipe['ingredients'] = recipe_details.get('extendedIngredients', [])

        if recipe_details['analyzedInstructions']:
            steps = recipe_details['analyzedInstructions'][0]['steps']
            recipe['steps'] = [step['step'] for step in steps]
        else:
            recipe['steps'] = []

        recipe['image'] = recipe_details.get('image', '')

    print([recipe['image'] for recipe in recipes])

    return recipes





# Application Routes
@app.route('/add_to_cart', methods=['POST'])
def add_to_cart():
    user_id = session['user_id']
    ingredient_name = request.form['ingredient_name']
    quantity = request.form['quantity']
    unit = request.form['unit']
    recipe_id = request.form['recipe_id']

    cart = Cart.query.filter_by(user_id=user_id).first()
    if not cart:
        cart = Cart(user_id=user_id)
        db.session.add(cart)
        db.session.commit()

    new_cart_item = CartItem(ingredient_name=ingredient_name, quantity=quantity, unit=unit, recipe_id=recipe_id, cart_id=cart.id)
    db.session.add(new_cart_item)
    db.session.commit()

    return jsonify({'message': 'Ingredient added to cart!'})

#@app.route('/')
#def index():
    #return render_template('index.html')

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # Retrieve the ingredient list from the form submission
        ingredients = request.form.get('ingredients')
        
        # Perform the search and get the search results in the `recipes` variable
        recipes = fetch_recipes(ingredients)
        
        # Render the template with the search results
        return render_template('index.html', recipes=recipes)
    
    # If it's a GET request or no search query is provided, render the template without search results
    return render_template('index.html')



@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if authenticate(username, password):
            session['user_id'] = User.query.filter_by(username=username).first().id
            flash('Logged in successfully!')
            return redirect(url_for('index'))
        else:
            flash('Invalid username or password.')
    return render_template('login.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        existing_user = User.query.filter_by(username=username).first()
        if existing_user is None:
            user = User(username=username)
            user.set_password(password)
            db.session.add(user)
            db.session.commit()
            flash('Registration successful!')
            return redirect(url_for('login'))
        else:
            flash('Username already exists.')
    return render_template('register.html')



@app.route('/search', methods=['GET', 'POST'])
def search():
    if request.method == 'POST':
        ingredients = request.form.get('ingredients')
        recipes = fetch_recipes(ingredients)
        for recipe in recipes:  # Print out each recipe's image URL
            print(recipe.image)
        print(f'Recipes passed to template: {recipes}')
        if not recipes:
            flash('Unable to fetch recipes. Please try again later.')
            return redirect(url_for('index'))
        else:
            return render_template('search_results.html', recipes=recipes)
    return render_template('search.html')






@app.route('/saved_recipes')
def saved_recipes():
    user_id = session['user_id']
    saved_recipes = SavedRecipe.query.filter_by(user_id=user_id).all()
    return render_template('saved_recipes.html', saved_recipes=saved_recipes)

@app.route('/save_recipe', methods=['POST'])
def save_recipe():
    if 'user_id' not in session:
        flash('Please log in or register to save recipes.')
        return redirect(url_for('login_or_register'))

    user_id = session['user_id']
    title = request.form['title']
    recipe_id = request.form['recipe_id']
    saved_recipe = SavedRecipe(title=title, recipe_id=recipe_id, user_id=user_id)
    db.session.add(saved_recipe)
    db.session.commit()
    flash('Recipe saved successfully!')
    return redirect(url_for('login_or_register'))


@app.route('/login_or_register', methods=['GET', 'POST'])
def login_or_register():
    if request.method == 'POST':
        form_type = request.form.get('form_type')

        if form_type == 'login':
            # process login form
            username = request.form['username']
            password = request.form['password']
            if authenticate(username, password):
                session['user_id'] = User.query.filter_by(username=username).first().id
                flash('Logged in successfully!')
                return redirect(url_for('index'))
            else:
                flash('Invalid username or password.')
                return render_template('login_or_register.html')

        elif form_type == 'register':
            # process register form
            username = request.form['username']
            password = request.form['password']
            existing_user = User.query.filter_by(username=username).first()
            if existing_user is None:
                user = User(username=username)
                user.set_password(password)
                db.session.add(user)
                db.session.commit()
                flash('Registration successful!')
                return redirect(url_for('login_or_register'))
            else:
                flash('Username already exists.')
                return render_template('login_or_register.html')

    # if request.method == 'GET'
    return render_template('login_or_register.html')



# Database Cleanup
@app.teardown_appcontext
def cleanup(resp_or_exc):
    db.session.remove()

# Application Execution
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)
