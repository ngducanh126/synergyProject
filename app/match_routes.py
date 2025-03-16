from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db

match_bp = Blueprint('match', __name__)

# Fetch other users for swiping
@match_bp.route('/get_others', methods=['GET'])
@jwt_required()
def get_other_users():
    """
    Fetch other users for swiping, excluding users the current user has already swiped right on
    or users they have already matched with (using the matches table).
    """
    current_user_id = get_jwt_identity()
    collaboration_id = request.args.get('collaboration_id', type=int)  # Optional parameter

    try:
        # Convert current_user_id to integer
        current_user_id = int(current_user_id)

        if collaboration_id:
            # Fetch users in the specified collaboration excluding swiped-right and matched users
            query = """
            SELECT u.id, u.username, u.bio, u.skills, u.location, u.profile_picture
            FROM users u
            JOIN user_collaborations uc ON u.id = uc.user_id
            WHERE uc.collaboration_id = :collaboration_id
              AND u.id != :current_user_id
              AND u.id NOT IN (
                  SELECT unnest(swipe_right) FROM users WHERE id = :current_user_id
              )
              AND u.id NOT IN (
                  SELECT CASE
                             WHEN user1_id = :current_user_id THEN user2_id
                             ELSE user1_id
                         END
                  FROM matches
                  WHERE :current_user_id IN (user1_id, user2_id)
              );
            """
            params = {'collaboration_id': collaboration_id, 'current_user_id': current_user_id}
        else:
            # Fetch all users excluding swiped-right and matched users
            query = """
            SELECT u.id, u.username, u.bio, u.skills, u.location, u.profile_picture
            FROM users u
            WHERE u.id != :current_user_id
              AND u.id NOT IN (
                  SELECT unnest(swipe_right) FROM users WHERE id = :current_user_id
              )
              AND u.id NOT IN (
                  SELECT CASE
                             WHEN user1_id = :current_user_id THEN user2_id
                             ELSE user1_id
                         END
                  FROM matches
                  WHERE :current_user_id IN (user1_id, user2_id)
              );
            """
            params = {'current_user_id': current_user_id}

        # Execute the query
        other_users = db.session.execute(query, params).fetchall()

        # Handle no users found
        if not other_users:
            print(f"[DEBUG] No other users found for user ID {current_user_id}.")
            return jsonify({'message': 'No other users available'}), 404

        # Prepare response data
        users_data = [
            {
                'id': user[0],
                'username': user[1],
                'bio': user[2],
                'skills': user[3],
                'location': user[4],
                'profile_picture': user[5],
            }
            for user in other_users
        ]

        print(f"[DEBUG] Retrieved {len(users_data)} other users for user ID {current_user_id}.")
        return jsonify(users_data), 200

    except Exception as e:
        print(f"[ERROR] Failed to fetch other users: {e}")
        return jsonify({'message': 'Failed to fetch other users'}), 500

# like (or "swipe right") a user
@match_bp.route('/swipe_right/<int:target_user_id>', methods=['POST'])
@jwt_required()
def swipe_right(target_user_id):
    """
    Handle the logic for swiping right on a user.
    Check for a mutual match and update the matches table if there's a match.
    """
    current_user_id = get_jwt_identity()

    try:
        # Convert current_user_id to integer
        current_user_id = int(current_user_id)

        # Fetch swipe_right list for the current user
        current_user_query = "SELECT swipe_right FROM users WHERE id = :current_user_id;"
        current_user = db.session.execute(current_user_query, {'current_user_id': current_user_id}).fetchone()

        # Ensure the current user exists
        if not current_user:
            return jsonify({'message': 'Current user not found'}), 404

        current_swipe_right = current_user[0] if current_user[0] else []

        # Ensure the target user exists
        target_user_query = "SELECT swipe_right FROM users WHERE id = :target_user_id;"
        target_user = db.session.execute(target_user_query, {'target_user_id': target_user_id}).fetchone()

        if not target_user:
            return jsonify({'message': 'Target user not found'}), 404

        target_swipe_right = target_user[0] if target_user[0] else []
        target_swipe_right = [int(user_id) for user_id in target_swipe_right]

        # Debugging: Print types and values
        print(f"[DEBUG] current_user_id: {current_user_id}, type: {type(current_user_id)}")
        print(f"[DEBUG] target_swipe_right: {target_swipe_right}, type: {type(target_swipe_right)}")
        print(f"[DEBUG] Current user swipe_right: {current_swipe_right}")

        # Prevent duplicate swipes
        if target_user_id in current_swipe_right:
            return jsonify({'message': 'Already swiped right'}), 400

        # Add the target user to the current user's swipe_right list
        current_swipe_right.append(target_user_id)
        db.session.execute(
            "UPDATE users SET swipe_right = :swipe_right WHERE id = :current_user_id;",
            {'swipe_right': current_swipe_right, 'current_user_id': current_user_id}
        )

        # Check for mutual match
        if current_user_id in target_swipe_right:
            print('yes match')
            # Add to the matches table
            db.session.execute(
                """
                INSERT INTO matches (user1_id, user2_id, matched_at)
                VALUES (:user1_id, :user2_id, NOW())
                ON CONFLICT DO NOTHING;
                """,
                {'user1_id': min(current_user_id, target_user_id),
                 'user2_id': max(current_user_id, target_user_id)}
            )

            print(f"[DEBUG] Match found: User {current_user_id} and User {target_user_id}")
            db.session.commit()

            return jsonify({'message': 'Swiped right successfully! It\'s a match!', 'is_match': True}), 200

        # Commit the swipe action
        db.session.commit()

        return jsonify({'message': 'Swiped right successfully', 'is_match': False}), 200

    except Exception as e:
        print(f"[ERROR] Failed to process swipe right for user {current_user_id} on user {target_user_id}: {e}")
        return jsonify({'message': 'Failed to process swipe right'}), 500


@match_bp.route('/matches', methods=['GET'])
@jwt_required()
def get_matches():
    """
    Fetch all users who are mutual matches with the current user using the matches table.
    """
    current_user_id = get_jwt_identity()

    try:
        # Convert current_user_id to integer
        current_user_id = int(current_user_id)

        # Fetch mutual matches from the matches table
        matches_query = """
        SELECT u.id, u.username, u.bio, u.skills, u.location, u.profile_picture
        FROM users u
        JOIN matches m ON u.id = m.user2_id
        WHERE m.user1_id = :current_user_id
        UNION
        SELECT u.id, u.username, u.bio, u.skills, u.location, u.profile_picture
        FROM users u
        JOIN matches m ON u.id = m.user1_id
        WHERE m.user2_id = :current_user_id;
        """
        matches = db.session.execute(matches_query, {'current_user_id': current_user_id}).fetchall()

        # Structure matched users' data
        matches_data = [
            {
                'id': user[0],
                'username': user[1],
                'bio': user[2],
                'skills': user[3],
                'location': user[4],
                'profile_picture': user[5],
            }
            for user in matches
        ]

        print(f"[DEBUG] Retrieved {len(matches_data)} matches for user ID {current_user_id}.")
        return jsonify(matches_data), 200

    except Exception as e:
        print(f"[ERROR] Failed to fetch matches for user ID {current_user_id}: {e}")
        return jsonify({'message': 'Failed to fetch matches.'}), 500


# Get collaborations of a specific user
@match_bp.route('/get_user_collaborations/<int:target_user_id>', methods=['GET'])
@jwt_required()
def get_user_collaborations(target_user_id):
    current_user_id = get_jwt_identity()

    try:
        # Fetch the target user's collaborations
        query = """
        SELECT c.id, c.name, c.description
        FROM collaborations c
        JOIN user_collaborations uc ON c.id = uc.collaboration_id
        WHERE uc.user_id = :target_user_id;
        """
        collaborations = db.session.execute(query, {'target_user_id': target_user_id}).fetchall()

        # Handle no collaborations case
        if not collaborations:
            print(f"[DEBUG] No collaborations found for user ID {target_user_id}.")
            return jsonify({'collaborations': []}), 200

        collaborations_data = [
            {'id': collab[0], 'name': collab[1], 'description': collab[2]}
            for collab in collaborations
        ]

        print(f"[DEBUG] Retrieved {len(collaborations_data)} collaborations for user ID {target_user_id}.")
        return jsonify({'collaborations': collaborations_data}), 200

    except Exception as e:
        print(f"[ERROR] Failed to fetch collaborations for user ID {target_user_id}: {e}")
        return jsonify({'message': 'Failed to fetch collaborations.'}), 500

    

@match_bp.route('/get_user/<int:user_id>', methods=['GET'])
@jwt_required()
def get_user(user_id):
    """
    Fetch all necessary information about a specific user by their ID,
    including whether the current user has already swiped right on them.
    """
    current_user_id = get_jwt_identity()  # The user making the request

    try:
        # Fetch user details
        user_query = """
        SELECT id, username, bio, skills, location, availability, profile_picture
        FROM users
        WHERE id = :user_id;
        """
        user = db.session.execute(user_query, {'user_id': user_id}).fetchone()

        if not user:
            print(f"[DEBUG] User with ID {user_id} not found.")
            return jsonify({'message': 'User not found'}), 404

        # Debug log for user details
        print(f"[DEBUG] Retrieved user: ID={user[0]}, Username={user[1]}, Profile Picture={user[6]}")

        # Check if the current user has already swiped right on the target user
        swipe_check_query = """
        SELECT :user_id = ANY(swipe_right)
        FROM users
        WHERE id = :current_user_id;
        """
        already_swiped = db.session.execute(swipe_check_query, {
            'user_id': user_id,
            'current_user_id': current_user_id,
        }).scalar()

        # Fetch collaborations where the user is a member or admin
        collaborations_query = """
        SELECT c.id, c.name, c.description
        FROM collaborations c
        JOIN user_collaborations uc ON c.id = uc.collaboration_id
        WHERE uc.user_id = :user_id;
        """
        collaborations = db.session.execute(collaborations_query, {'user_id': user_id}).fetchall()

        # Structure collaborations data
        collaborations_data = [
            {'id': collab[0], 'name': collab[1], 'description': collab[2]}
            for collab in collaborations
        ]

        # Fetch collections for the user (if applicable)
        collections_query = """
        SELECT id, name
        FROM collections
        WHERE user_id = :user_id;
        """
        collections = db.session.execute(collections_query, {'user_id': user_id}).fetchall()

        # Structure collections data
        collections_data = [
            {'id': collection[0], 'name': collection[1]}
            for collection in collections
        ]

        # Combine all user data
        user_data = {
            'id': user[0],
            'username': user[1],
            'bio': user[2],
            'skills': user[3],
            'location': user[4],
            'availability': user[5],
            'profile_picture': user[6],
            'collaborations': collaborations_data,
            'collections': collections_data,
            'already_swiped_right': already_swiped,  # Add swipe right status
        }

        print("[DEBUG] Final user data response:")
        print(user_data)

        return jsonify(user_data), 200

    except Exception as e:
        print(f"[ERROR] Failed to fetch user details for user ID {user_id}: {e}")
        return jsonify({'message': 'Failed to fetch user details'}), 500



@match_bp.route('/likes', methods=['GET'])
@jwt_required()
def likes():
    """
    Get all users who swiped right on the logged-in user, excluding users they have already matched with.
    """
    current_user_id = get_jwt_identity()  # The ID of the logged-in user

    try:
        # Fetch users who liked the current user but are not mutual matches
        query = """
        SELECT id, username, bio, skills, location, profile_picture
        FROM users
        WHERE :current_user_id = ANY(swipe_right)
          AND id NOT IN (
              SELECT CASE
                         WHEN user1_id = :current_user_id THEN user2_id
                         ELSE user1_id
                     END
              FROM matches
              WHERE :current_user_id IN (user1_id, user2_id)
          );
        """
        liked_users = db.session.execute(query, {'current_user_id': current_user_id}).fetchall()

        # Handle case where no users are found
        if not liked_users:
            print(f"[DEBUG] No users found who liked user ID {current_user_id}.")
            return jsonify({'message': 'No users have liked you yet.'}), 404

        # Structure liked users' data
        liked_users_data = [
            {
                'id': user[0],
                'username': user[1],
                'bio': user[2],
                'skills': user[3],
                'location': user[4],
                'profile_picture': user[5],
            }
            for user in liked_users
        ]

        print(f"[DEBUG] Retrieved {len(liked_users_data)} users who liked user ID {current_user_id}.")
        return jsonify(liked_users_data), 200

    except Exception as e:
        print(f"[ERROR] Failed to fetch users who liked user ID {current_user_id}: {e}")
        return jsonify({'message': 'Failed to fetch users who liked you.'}), 500
@match_bp.route('/block_user/<int:user_id>', methods=['POST'])
@jwt_required()
def block_user(user_id):
    return jsonify({'message': 'User blocked.'}), 200

@match_bp.route('/unblock_user/<int:user_id>', methods=['POST'])
@jwt_required()
def unblock_user(user_id):
    return jsonify({'message': 'User unblocked.'}), 200

@match_bp.route('/blocked_users', methods=['GET'])
@jwt_required()
def get_blocked_users():
    return jsonify({'blocked_users': []}), 200

@match_bp.route('/report_user/<int:user_id>', methods=['POST'])
@jwt_required()
def report_user(user_id):
    return jsonify({'message': 'User reported.'}), 200

@match_bp.route('/super_like/<int:user_id>', methods=['POST'])
@jwt_required()
def super_like_user(user_id):
    return jsonify({'message': 'Super liked user.'}), 200

@match_bp.route('/undo_swipe/<int:user_id>', methods=['POST'])
@jwt_required()
def undo_swipe(user_id):
    return jsonify({'message': 'Swipe undone.'}), 200

@match_bp.route('/recently_viewed', methods=['GET'])
@jwt_required()
def recently_viewed():
    return jsonify({'recently_viewed': []}), 200

@match_bp.route('/favorite_user/<int:user_id>', methods=['POST'])
@jwt_required()
def favorite_user(user_id):
    return jsonify({'message': 'User favorited.'}), 200

@match_bp.route('/favorites', methods=['GET'])
@jwt_required()
def get_favorites():
    return jsonify({'favorites': []}), 200

@match_bp.route('/remove_favorite/<int:user_id>', methods=['POST'])
@jwt_required()
def remove_favorite(user_id):
    return jsonify({'message': 'Favorite removed.'}), 200

@match_bp.route('/match_activity', methods=['GET'])
@jwt_required()
def match_activity():
    return jsonify({'activity': []}), 200

@match_bp.route('/match_notes/<int:match_id>', methods=['GET'])
@jwt_required()
def get_match_notes(match_id):
    return jsonify({'notes': []}), 200

@match_bp.route('/add_match_note/<int:match_id>', methods=['POST'])
@jwt_required()
def add_match_note(match_id):
    return jsonify({'message': 'Note added to match.'}), 200

@match_bp.route('/delete_match_note/<int:note_id>', methods=['DELETE'])
@jwt_required()
def delete_match_note(note_id):
    return jsonify({'message': 'Note deleted.'}), 200

@match_bp.route('/rematch/<int:user_id>', methods=['POST'])
@jwt_required()
def rematch_user(user_id):
    return jsonify({'message': 'Rematch requested.'}), 200

@match_bp.route('/match_feedback/<int:match_id>', methods=['POST'])
@jwt_required()
def match_feedback(match_id):
    return jsonify({'message': 'Feedback submitted.'}), 200

@match_bp.route('/pending_matches', methods=['GET'])
@jwt_required()
def pending_matches():
    return jsonify({'pending_matches': []}), 200

@match_bp.route('/accept_match/<int:match_id>', methods=['POST'])
@jwt_required()
def accept_match(match_id):
    return jsonify({'message': 'Match accepted.'}), 200

@match_bp.route('/reject_match/<int:match_id>', methods=['POST'])
@jwt_required()
def reject_match(match_id):
    return jsonify({'message': 'Match rejected.'}), 200

@match_bp.route('/match_history', methods=['GET'])
@jwt_required()
def match_history():
    return jsonify({'history': []}), 200

@match_bp.route('/mute_user/<int:user_id>', methods=['POST'])
@jwt_required()
def mute_user(user_id):
    return jsonify({'message': 'User muted.'}), 200

@match_bp.route('/unmute_user/<int:user_id>', methods=['POST'])
@jwt_required()
def unmute_user(user_id):
    return jsonify({'message': 'User unmuted.'}), 200

@match_bp.route('/muted_users', methods=['GET'])
@jwt_required()
def get_muted_users():
    return jsonify({'muted_users': []}), 200

@match_bp.route('/hide_match/<int:match_id>', methods=['POST'])
@jwt_required()
def hide_match(match_id):
    return jsonify({'message': 'Match hidden.'}), 200

@match_bp.route('/unhide_match/<int:match_id>', methods=['POST'])
@jwt_required()
def unhide_match(match_id):
    return jsonify({'message': 'Match unhidden.'}), 200

@match_bp.route('/hidden_matches', methods=['GET'])
@jwt_required()
def get_hidden_matches():
    return jsonify({'hidden_matches': []}), 200

@match_bp.route('/send_gift/<int:user_id>', methods=['POST'])
@jwt_required()
def send_gift(user_id):
    return jsonify({'message': 'Gift sent.'}), 200

@match_bp.route('/received_gifts', methods=['GET'])
@jwt_required()
def received_gifts():
    return jsonify({'gifts': []}), 200

@match_bp.route('/sent_gifts', methods=['GET'])
@jwt_required()
def sent_gifts():
    return jsonify({'gifts': []}), 200

@match_bp.route('/boost_profile', methods=['POST'])
@jwt_required()
def boost_profile():
    return jsonify({'message': 'Profile boosted.'}), 200

@match_bp.route('/profile_boosts', methods=['GET'])
@jwt_required()
def profile_boosts():
    return jsonify({'boosts': []}), 200

@match_bp.route('/send_message/<int:match_id>', methods=['POST'])
@jwt_required()
def send_message(match_id):
    return jsonify({'message': 'Message sent.'}), 200

@match_bp.route('/messages/<int:match_id>', methods=['GET'])
@jwt_required()
def get_messages(match_id):
    return jsonify({'messages': []}), 200

