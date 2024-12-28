from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db

match_bp = Blueprint('match', __name__)

# Fetch other users for swiping
@match_bp.route('/get_others', methods=['GET'])
@jwt_required()
def get_other_users():
    current_user_id = get_jwt_identity()
    collaboration_id = request.args.get('collaboration_id', type=int)  # Optional parameter

    if collaboration_id:
        # Fetch other users in the specified collaboration
        query = """
        SELECT u.id, u.username, u.bio, u.skills, u.location
        FROM users u
        JOIN user_collaborations uc ON u.id = uc.user_id
        WHERE uc.collaboration_id = :collaboration_id AND u.id != :current_user_id;
        """
        params = {'collaboration_id': collaboration_id, 'current_user_id': current_user_id}
    else:
        # Fetch all other users who are not the current user
        query = """
        SELECT id, username, bio, skills, location
        FROM users
        WHERE id != :current_user_id;
        """
        params = {'current_user_id': current_user_id}

    other_users = db.session.execute(query, params).fetchall()

    if not other_users:
        return jsonify({'message': 'No other users available'}), 404

    users_data = [
        {
            'id': user[0],
            'username': user[1],
            'bio': user[2],
            'skills': user[3],
            'location': user[4],
        }
        for user in other_users
    ]

    return jsonify(users_data), 200



# Swipe right on a user
@match_bp.route('/swipe_right/<int:target_user_id>', methods=['POST'])
@jwt_required()
def swipe_right(target_user_id):
    current_user_id = get_jwt_identity()

    # Check if the target user exists
    target_user_query = "SELECT id, swipe_right FROM users WHERE id = :target_user_id;"
    target_user = db.session.execute(target_user_query, {'target_user_id': target_user_id}).fetchone()

    if not target_user:
        return jsonify({'message': 'Target user not found'}), 404

    # Fetch and update current user's swipe_right
    current_user_query = "SELECT swipe_right FROM users WHERE id = :current_user_id;"
    current_user = db.session.execute(current_user_query, {'current_user_id': current_user_id}).fetchone()

    swipe_right_list = current_user[0] if current_user and current_user[0] else []
    if target_user_id in swipe_right_list:
        return jsonify({'message': 'Already swiped right'}), 400

    swipe_right_list.append(target_user_id)
    update_swipe_query = "UPDATE users SET swipe_right = :swipe_right WHERE id = :current_user_id;"
    db.session.execute(update_swipe_query, {'swipe_right': swipe_right_list, 'current_user_id': current_user_id})

    # Check for mutual match
    is_match = False
    if current_user_id in (target_user[1] if target_user[1] else []):
        # Fetch matches for both users
        fetch_matches_query = "SELECT matches FROM users WHERE id = :user_id;"
        current_user_matches = db.session.execute(fetch_matches_query, {'user_id': current_user_id}).fetchone()
        target_user_matches = db.session.execute(fetch_matches_query, {'user_id': target_user_id}).fetchone()

        current_user_matches = current_user_matches[0] if current_user_matches and current_user_matches[0] else []
        target_user_matches = target_user_matches[0] if target_user_matches and target_user_matches[0] else []

        current_user_matches.append(target_user_id)
        target_user_matches.append(current_user_id)

        update_matches_query = "UPDATE users SET matches = :matches WHERE id = :user_id;"
        db.session.execute(update_matches_query, {'matches': current_user_matches, 'user_id': current_user_id})
        db.session.execute(update_matches_query, {'matches': target_user_matches, 'user_id': target_user_id})

        is_match = True

    db.session.commit()

    if is_match:
        return jsonify({'message': 'Swiped right successfully! It\'s a match!', 'is_match': True}), 200

    return jsonify({'message': 'Swiped right successfully', 'is_match': False}), 200


# Get Matches
@match_bp.route('/matches', methods=['GET'])
@jwt_required()
def get_matches():
    current_user_id = get_jwt_identity()

    # Fetch current user's swipe_right list
    current_user_query = "SELECT swipe_right FROM users WHERE id = :current_user_id;"
    current_user = db.session.execute(current_user_query, {'current_user_id': current_user_id}).fetchone()

    if not current_user or not current_user[0]:
        return jsonify({'message': 'No matches yet!'}), 404

    # List of users the current user has liked
    liked_users = current_user[0]

    # Check if those users have also liked the current user
    mutual_matches = []
    for liked_user_id in liked_users:
        liked_user_query = "SELECT swipe_right FROM users WHERE id = :liked_user_id;"
        liked_user = db.session.execute(liked_user_query, {'liked_user_id': liked_user_id}).fetchone()

        if liked_user and liked_user[0]:
            # Check for mutual match
            if int(current_user_id) in [int(id) for id in liked_user[0]]:
                mutual_matches.append(liked_user_id)

    if not mutual_matches:
        return jsonify({'message': 'No matches yet!'}), 404

    # Fetch matched users' profiles
    matches_query = """
    SELECT id, username, bio, skills, location
    FROM users
    WHERE id = ANY(:mutual_matches);
    """
    matches = db.session.execute(matches_query, {'mutual_matches': mutual_matches}).fetchall()

    matches_data = [
        {
            'id': user[0],
            'username': user[1],
            'bio': user[2],
            'skills': user[3],
            'location': user[4],
        }
        for user in matches
    ]

    return jsonify(matches_data), 200
