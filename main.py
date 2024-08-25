from flask import Flask, render_template, redirect, url_for, request
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import Integer, String
from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, IntegerField
from wtforms.validators import DataRequired, NumberRange
from themoviedb import TMDb
import os
SECRET_KEY = os.urandom(32)


app = Flask(__name__)
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://user:password@my-db-service/db'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = SECRET_KEY
Bootstrap5(app)

tmdb = TMDb(key="b15361d2d30494279d40ba2f228ac5cd")


class Base(DeclarativeBase):
    pass


db = SQLAlchemy(model_class=Base)
db.init_app(app)


class Movie(db.Model):
    ranking: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str] = mapped_column(String(250), unique=True, nullable=False)
    year: Mapped[int] = mapped_column(Integer, nullable=False)
    description: Mapped[str] = mapped_column(String(250), nullable=False)
    rating: Mapped[int] = mapped_column(Integer, nullable=False)
    review: Mapped[str] = mapped_column(String(250), nullable=False)
    img_url: Mapped[str] = mapped_column(String(250), nullable=False)


class MyForm(FlaskForm):
    rating = IntegerField('Rating', validators=[DataRequired(), NumberRange(1, 10)], render_kw={"placeholder": "test"})
    review = StringField('Review', validators=[DataRequired()])
    submit = SubmitField("Done")


class AddForm(FlaskForm):
    title = StringField('Movie Title', validators=[DataRequired()])
    submit = SubmitField("Add")


with app.app_context():
    db.create_all()


@app.route("/")
def home():
    result = db.session.execute(db.select(Movie))
    all_movies = result.scalars().all()
    return render_template("index.html", movies=all_movies)


@app.route("/edit", methods=["GET", "POST"])
def edit():
    movie_ranking = request.args.get('ranking')
    movie_to_update = db.get_or_404(Movie, movie_ranking)
    form = MyForm(obj=movie_to_update)
    if form.validate_on_submit():
        movie_to_update.rating = form.rating.data
        movie_to_update.review = form.review.data
        db.session.commit()
        result = db.session.execute(db.select(Movie))
        all_movies = result.scalars().all()
        return render_template('index.html', movies=all_movies)
    return render_template('edit.html', form=form, movie=movie_to_update)


@app.route("/delete")
def delete():
    movie_ranking = request.args.get("ranking")
    movie_to_delete = db.get_or_404(Movie, movie_ranking)
    db.session.delete(movie_to_delete)

    movies_to_update = db.session.execute(
        db.select(Movie).where(Movie.ranking > movie_ranking)
    ).scalars().all()
    for movie_to_update in movies_to_update:
        movie_to_update.ranking -= 1

    db.session.commit()
    return redirect(url_for("home"))


@app.route("/add", methods=["POST", "GET"])
def add():
    form = AddForm()
    if form.validate_on_submit():
        movie_to_add = form.title.data
        return redirect(f'/select?movie={movie_to_add}')
    return render_template('add.html', form=form)


@app.route("/select")
def select():
    movie_to_add = request.args.get('movie')
    movies = tmdb.search().movies(movie_to_add)
    return render_template('select.html', movies=movies)


@app.route("/movie")
def movie():
    movie_id = int(request.args.get('id'))
    movie_to_add = tmdb.movie(movie_id).details(append_to_response="images")

    highest_ranking_movie = db.session.execute(
        db.select(Movie).order_by(Movie.ranking.desc())
    ).scalars().first()

    if highest_ranking_movie:
        new_ranking = highest_ranking_movie.ranking + 1
    else:
        new_ranking = 1

    mv = Movie(
        ranking=new_ranking,
        title=movie_to_add.title,
        year=movie_to_add.year,
        description=movie_to_add.overview,
        rating=0,
        review="",
        img_url=movie_to_add.poster_url()
    )
    db.session.add(mv)
    db.session.commit()

    # return redirect(url_for("home"))
    return redirect(url_for('edit', ranking=new_ranking))


if __name__ == '__main__':
    app.run(debug=True)
