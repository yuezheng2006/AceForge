"""
Users API for new UI. No auth; stubs return fixed local user / empty lists.
Contract matches Express for compatibility.
"""

from flask import Blueprint, jsonify

from api.auth import LOCAL_USER

bp = Blueprint("api_users", __name__)


@bp.route("/me", methods=["GET"])
def get_me():
    return jsonify({"user": LOCAL_USER})


@bp.route("/public/featured", methods=["GET"])
def list_featured():
    return jsonify({"creators": []})


@bp.route("/<username>", methods=["GET"])
def get_profile(username: str):
    return jsonify({"user": {**LOCAL_USER, "username": username or LOCAL_USER["username"]}})


@bp.route("/<username>/songs", methods=["GET"])
def get_user_songs(username: str):
    from api.songs import list_songs
    return list_songs()


@bp.route("/<username>/playlists", methods=["GET"])
def get_user_playlists(username: str):
    from api.playlists import list_playlists
    return list_playlists()


@bp.route("/me", methods=["PATCH"])
def update_me():
    return jsonify({"user": LOCAL_USER})


@bp.route("/me/avatar", methods=["POST"])
def upload_avatar():
    return jsonify({"user": LOCAL_USER, "url": None})


@bp.route("/me/banner", methods=["POST"])
def upload_banner():
    return jsonify({"user": LOCAL_USER, "url": None})


@bp.route("/<username>/follow", methods=["POST"])
def follow(username: str):
    return jsonify({"following": False, "followerCount": 0})


@bp.route("/<username>/followers", methods=["GET"])
def get_followers(username: str):
    return jsonify({"followers": []})


@bp.route("/<username>/following", methods=["GET"])
def get_following(username: str):
    return jsonify({"following": []})


@bp.route("/<username>/stats", methods=["GET"])
def get_stats(username: str):
    return jsonify({"followerCount": 0, "followingCount": 0, "isFollowing": False})
