# Improved Flask app

from flask import Flask, render_template, request, redirect, url_for, flash, session ,send_from_directory ,blueprints , Blueprint
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from datetime import datetime
import os
import uuid
app = Flask(__name__, template_folder='templates', static_folder='static', static_url_path='/static')

# Use environment variables for sensitive information
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'mysecretkey')
# max upload size 100MB
app.config['MAX_CONTENT_LENGTH'] = 300 * 1024 * 1024
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', 'sqlite:///db.sqlite3')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['ALLOWED_EXTENSIONS'] = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mp3', 'doc', 'docx', 'ppt', 'pptx', 'xls', 'xlsx'}
app.config['UPLOAD_FOLDER'] = 'uploads'

db = SQLAlchemy(app)
migrate = Migrate(app, db)

class Post(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      title = db.Column(db.String(255), nullable=False)
      category = db.Column(db.String(255), nullable=False)
      content = db.Column(db.Text, nullable=False)
      banner = db.Column(db.String(255), nullable=True)
      views = db.Column(db.Integer, default=0)
      status = db.Column(db.String(50), default='draft')  # draft, published
      created_at = db.Column(db.DateTime, default=datetime.utcnow)
      updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
      media = db.relationship('Media', backref='post', lazy=True)

class Media(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      name = db.Column(db.String(255), nullable=False)
      post_id = db.Column(db.Integer, db.ForeignKey('post.id'), nullable=False)
      media_type = db.Column(db.String(50), nullable=False) # image, video, audio, document 
      url = db.Column(db.String(255), nullable=False)
      status = db.Column(db.String(50), default='draft')  # draft, published
      created_at = db.Column(db.DateTime, default=datetime.utcnow)

class User(db.Model):
      id = db.Column(db.Integer, primary_key=True)
      username = db.Column(db.String(255), unique=True, nullable=False)
      password = db.Column(db.String(255), nullable=False)
      email = db.Column(db.String(255), unique=True, nullable=False)
      status = db.Column(db.String(50), default='active')  # active, inactive
      created_at = db.Column(db.DateTime, default=datetime.utcnow)
      updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


# blueprint for admin routes

admin = Blueprint('admin', __name__, url_prefix='/admin')

def save_file(file):
    filename = file.filename
    if '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']:
        file_ext = filename.rsplit('.', 1)[1].lower()
        filename = str(uuid.uuid4()) + '.' + file_ext
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        return filename
    return None


@app.route('/')
def index():
      # demo posts data 
      posts = [{
            'id': 1,
            'title': 'Post Title',
            'category': 'News',
            'content': 'Post Content text here to be displayed in the post preview section in the home page or the posts page or the post page itself.',
            'banner': 'banner.jpg',
            'views': 100,
            'status': 'published',
            'created_at': datetime.utcnow(),
            'updated_at': datetime.utcnow()
      }]
      return render_template('public/list.html', PageName='الاخبار', posts=posts)

@app.route('/posts/<category>')
def posts(category):
      posts = Post.query.filter_by(category=category).all()
      if not posts:
            flash('No posts found', 'danger')
            return redirect(url_for('index'))
      return render_template('public/list.html', PageName=category, posts=posts)
@app.route('/post/<int:id>')
def post(id):
    post = Post.query.get_or_404(id)
    post.views += 1  
    db.session.commit()
    media = Media.query.filter_by(post_id=id).all()  # Retrieve all media associated with the post
    return render_template('public/post.html', post=post, media=media)


# respoens with data from the uploads folder
@app.route('/uploads/<filename>')
def uploaded_file(filename):
      return send_from_directory(app.config['UPLOAD_FOLDER'], filename)




@admin.route('/')
def index():
    # Example static data for the cards
    stats = {
        'media_count': Media.query.count(),
        'post_views': sum(post.views for post in Post.query.all()),
        'storage_used': '15GB',  # Assuming you calculate this somehow
        'visitors_count': 1200  # Example count
    }
    # Fetch data for the table (last 10 posts)
    latest_table_posts = Post.query.order_by(Post.created_at.desc()).limit(10).all()

    return render_template('admin/index.html', stats=stats, latest_table_posts=latest_table_posts)

@admin.route('/list/<category>')
def list(category):
      posts = Post.query.filter_by(category=category).all()
      return render_template('admin/list.html', latest_table_posts=posts,category=category)


# add_post
@admin.route('/add', methods=['GET', 'POST'])
def add_post():
      if request.method == 'POST':
            title = request.form['title']
            category = request.form['category']
            content = request.form['content']
            banner = request.files['image']
            status = request.form['status']

            post = Post(title=title, category=category, content=content, banner=save_file(banner), status=status)
            db.session.add(post)
            db.session.commit()
            flash('Post added successfully', 'success')
            return redirect(url_for('admin.index'))
      return render_template('admin/add.html')

@admin.route('/post/<int:id>', methods=['GET', 'POST'])
def post(id):
    post = Post.query.get_or_404(id)
    media_items = Media.query.filter_by(post_id=id).all()

    if request.method == 'POST':
        print(request.files)
        file = request.files.get('file')
        media_type = request.form.get('media_type')
        if file and media_type :
            filename = save_file(file)
            if filename:
                new_media = Media(name=filename, post_id=id, media_type=media_type, url=os.path.join(app.config['UPLOAD_FOLDER'], filename))
                db.session.add(new_media)
                db.session.commit()
                flash('Media added successfully', 'success')
            else:
                flash('Failed to save file', 'danger')
        else:
            flash('Invalid file type', 'warning')

    return render_template('admin/post.html', post=post, media_items=media_items)

# admin.edit_post
@admin.route('/edit/<int:id>', methods=['GET', 'POST'])
def edit_post(id):
      post = Post.query.get(id)
      if request.method == 'POST':
            post.title = request.form['title']
            post.category = request.form['category']
            post.content = request.form['content']

            post.status = request.form['status']
            db.session.commit()
            flash('Post updated successfully', 'success')
            return redirect(url_for('admin.post', id=post.id))
      return render_template('admin/edit.html', post=post)
# admin.delete_post
@admin.route('/delete/<int:id>')
def delete_post(id):
      post = Post.query.get(id)
      db.session.delete(post)
      db.session.commit()
      flash('Post deleted successfully', 'success')
      return redirect(url_for('admin.index'))

# admin.delete_media
@admin.route('/media/delete/<int:id>')
def delete_media(id):
    media = Media.query.get(id)
    db.session.delete(media)
    db.session.commit()
    flash('Media deleted successfully', 'success')
    return redirect(url_for('admin.post', id=media.post_id))

# register the blueprint
app.register_blueprint(admin)

if __name__ == '__main__':
      with app.app_context():
            db.create_all()
      app.run(debug=false, host='0.0.0.0', port=5000, use_reloader=True)

