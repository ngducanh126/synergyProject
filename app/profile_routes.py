from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
import boto3
import mimetypes
import tempfile
import os
from botocore.exceptions import NoCredentialsError
from botocore.config import Config as BotoConfig
from app.config import Config

profile_bp = Blueprint('profile', __name__)

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS

def save_file(file, path, s3_object_name=None):
    """Save a file either locally or to AWS S3 based on the configuration."""
    file_path = None

    try:

        # Create S3 client
        s3 = boto3.client(
            's3',
            aws_access_key_id=Config.AWS_ACCESS_KEY,
            aws_secret_access_key=Config.AWS_SECRET_KEY,
            region_name=Config.AWS_REGION,
            config=BotoConfig(connect_timeout=5, read_timeout=10, retries={'max_attempts': 3})
        )

        # Save file temporarily
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name

        # Detect content type
        content_type, _ = mimetypes.guess_type(temp_file_path)
        content_type = content_type or "application/octet-stream"

        # Upload to S3
        with open(temp_file_path, "rb") as file_data:
            s3.put_object(
                Bucket=Config.AWS_BUCKET_NAME,
                Key=s3_object_name,
                Body=file_data,
                ContentType=content_type,
            )
        file_path = f"https://{Config.AWS_BUCKET_NAME}.s3.{Config.AWS_REGION}.amazonaws.com/{s3_object_name}"

        # Clean up temporary file
        os.unlink(temp_file_path)


    except Exception as e:
        print(f"[ERROR] Failed to save file: {e}")
        raise

    return file_path

def save_profile_picture(file, entity_id, entity_type='users', is_edit=False):
    """Save profile picture for a user or collection."""
    file_extension = file.filename.rsplit('.', 1)[1].lower()
    filename = f"profile_pic.{file_extension}" if is_edit else file.filename


    s3_object_name = f"{entity_type}/{entity_id}/{filename}"
    return save_file(file, None, s3_object_name)


@profile_bp.route('/view', methods=['GET'])
@jwt_required()
def view_profile():
    user_id = get_jwt_identity()

    try:
        user_query = """
        SELECT id, username, bio, skills, location, availability, verification_status, profile_picture
        FROM users
        WHERE id = :user_id;
        """
        user = db.session.execute(user_query, {'user_id': user_id}).fetchone()

        if not user:
            return jsonify({'message': 'User not found'}), 404

        collaborations_query = """
        SELECT c.id, c.name, c.description, 
               CASE 
                   WHEN c.admin_id = :user_id THEN 'admin'
                   ELSE 'member'
               END AS role
        FROM collaborations c
        LEFT JOIN user_collaborations uc ON c.id = uc.collaboration_id AND uc.user_id = :user_id
        WHERE c.admin_id = :user_id OR uc.user_id = :user_id;
        """
        collaborations = db.session.execute(collaborations_query, {'user_id': user_id}).fetchall()

        collaborations_data = [
            {
                'id': collab[0],
                'name': collab[1],
                'description': collab[2],
                'role': collab[3]
            } for collab in collaborations
        ]

        user_data = {
            'id': user[0],
            'username': user[1],
            'bio': user[2],
            'skills': user[3],
            'location': user[4],
            'availability': user[5],
            'verification_status': user[6],
            'profile_picture': user[7],
            'collaborations': collaborations_data,
        }

        return jsonify(user_data), 200
    except Exception as e:
        return jsonify({'message': 'Failed to fetch profile', 'error': str(e)}), 500

@profile_bp.route('/update', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = get_jwt_identity()
    print(f"[DEBUG] Received request to update profile for user_id: {user_id}")

    try:
        user_query = "SELECT id FROM users WHERE id = :user_id;"
        user = db.session.execute(user_query, {'user_id': user_id}).fetchone()
        if not user:
            return jsonify({'message': 'User not found'}), 404
    except Exception as db_error:
        return jsonify({'message': 'Database query failed', 'error': str(db_error)}), 500

    bio = request.form.get('bio')
    skills = request.form.get('skills')
    location = request.form.get('location')
    availability = request.form.get('availability')
    file = request.files.get('profile_picture')

    profile_picture_path = None
    if file:
        try:
            profile_picture_path = save_profile_picture(file, user_id)
        except Exception as e:
            return jsonify({'message': 'Failed to upload profile picture', 'error': str(e)}), 500

    if skills:
        skills = "{" + ",".join(skill.strip() for skill in skills.split(',')) + "}"

    update_query = """
    UPDATE users
    SET bio = COALESCE(:bio, bio),
        skills = COALESCE(:skills, skills),
        location = COALESCE(:location, location),
        availability = COALESCE(:availability, availability),
        profile_picture = COALESCE(:profile_picture, profile_picture)
    WHERE id = :user_id;
    """
    try:
        db.session.execute(
            update_query,
            {
                'bio': bio,
                'skills': skills,
                'location': location,
                'availability': availability,
                'profile_picture': profile_picture_path,
                'user_id': user_id,
            },
        )
        db.session.commit()
        return jsonify({'message': 'Profile updated successfully', 'profile_picture_url': profile_picture_path}), 200
    except Exception as db_error:
        return jsonify({'message': 'Failed to update profile', 'error': str(db_error)}), 500



# Fetch other users' profiles
@profile_bp.route('/get_others', methods=['GET'])
@jwt_required()
def get_other_users():
    """
    Fetch all other users except the current user, optionally filtered by collaboration ID.
    """
    current_user_id = get_jwt_identity()
    collaboration_id = request.args.get('collaboration_id', type=int)  # Optional filter

    try:
        if collaboration_id:
            # Fetch other users in the specified collaboration
            query = """
            SELECT u.id, u.username, u.bio, u.skills, u.location, u.profile_picture
            FROM users u
            JOIN user_collaborations uc ON u.id = uc.user_id
            WHERE uc.collaboration_id = :collaboration_id AND u.id != :current_user_id;
            """
            params = {'collaboration_id': collaboration_id, 'current_user_id': current_user_id}
        else:
            # Fetch all other users except the current user
            query = """
            SELECT id, username, bio, skills, location, profile_picture
            FROM users
            WHERE id != :current_user_id;
            """
            params = {'current_user_id': current_user_id}

        other_users = db.session.execute(query, params).fetchall()

        if not other_users:
            print(f"[DEBUG] No other users found for user ID {current_user_id}.")
            return jsonify({'message': 'No other users available'}), 404

        # Format the response data
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
    

# create a collection for current user ( name, descriotion, profile picture for collection)
@profile_bp.route('/collections', methods=['POST'])
@jwt_required()
def create_collection():
    user_id = get_jwt_identity()  # Get the current logged-in user's ID

    # Check if the collection name is provided in the request body
    data = request.get_json()
    collection_name = data.get('name')

    if not collection_name:
        return jsonify({'message': 'Collection name is required'}), 400

    try:
        # Insert the new collection into the collections table
        query = """
        INSERT INTO collections (user_id, name)
        VALUES (:user_id, :name)
        RETURNING id;
        """
        result = db.session.execute(query, {'user_id': user_id, 'name': collection_name})
        db.session.commit()

        # Get the ID of the newly created collection
        collection_id = result.fetchone()[0]

        return jsonify({'id': collection_id, 'name': collection_name}), 201

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to create collection'}), 500

@profile_bp.route('/collections/<int:collection_id>/items', methods=['POST'])
@jwt_required()
def add_item_to_collection(collection_id):
    try:
        user_id = get_jwt_identity()
        item_type = request.form.get('type')
        content = request.form.get('content')
        file = request.files.get('file')

        file_path = None
        if file:
            original_filename = file.filename
            s3_object_name = f"collections/{collection_id}/{original_filename}"
            file_path = save_file(file, None, s3_object_name)

        if not item_type or not content:
            return jsonify({'error': 'Type and content are required fields'}), 400

        query = """
        INSERT INTO collection_items (collection_id, type, content, file_path)
        VALUES (:collection_id, :type, :content, :file_path)
        """
        db.session.execute(query, {
            'collection_id': collection_id,
            'type': item_type,
            'content': content,
            'file_path': file_path
        })
        db.session.commit()

        return jsonify({'message': 'Item added to collection successfully', 'file_path': file_path}), 201
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# getting my collections
@profile_bp.route('/collections', methods=['GET'])
@jwt_required()
def get_collections():
    user_id = get_jwt_identity()
    print(f"[DEBUG] Fetching collections for user_id: {user_id}")

    query = "SELECT id, name FROM collections WHERE user_id = :user_id"
    collections = db.session.execute(query, {'user_id': user_id}).fetchall()

    collections_data = [{'id': col[0], 'name': col[1]} for col in collections]
    print(f"[DEBUG] Retrieved collections: {collections_data}")
    return jsonify(collections_data), 200

# Getting collections for another user
@profile_bp.route('/collections/<int:collection_id>', methods=['GET'])
@jwt_required()
def get_collection_items(collection_id):
    try:
        print(f"[DEBUG] Fetching items for Collection ID: {collection_id}")

        query = """
        SELECT id, type, content, file_path FROM collection_items WHERE collection_id = :collection_id
        """
        items = db.session.execute(query, {'collection_id': collection_id}).fetchall()
        print(f"[DEBUG] Raw items from database: {items}")

        items_data = []
        for item in items:
            if item[3]:  # Check if file_path exists
                # Use the file_path as is if it already contains a full URL
                if item[3].startswith("http://") or item[3].startswith("https://"):
                    normalized_file_path = item[3]
                else:
                    # Otherwise, prepend with the base URL dynamically
                    base_url = request.host_url.rstrip('/')  # Removes trailing slash
                    normalized_file_path = f"{base_url}/{item[3]}"
            else:
                normalized_file_path = None

            print(f"[DEBUG] Normalizing file path: {item[3]} -> {normalized_file_path}")

            items_data.append({
                'id': item[0],
                'type': item[1],
                'content': item[2],
                'file_path': normalized_file_path
            })

        print(f"[DEBUG] Items data prepared for response: {items_data}")
        return jsonify(items_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': str(e)}), 500



# delete one of my collections
@profile_bp.route('/collections/<int:collection_id>', methods=['DELETE'])
@jwt_required()
def delete_collection(collection_id):
    print(f"[DEBUG] Deleting collection_id: {collection_id}")

    query = "DELETE FROM collections WHERE id = :collection_id"
    db.session.execute(query, {'collection_id': collection_id})
    db.session.commit()

    print(f"[DEBUG] Collection deleted: {collection_id}")
    return jsonify({'message': 'Collection deleted successfully'}), 200


# delete an item from one of my collection
@profile_bp.route('/collections/<int:collection_id>/items/<int:item_id>', methods=['DELETE'])
@jwt_required()
def delete_item(collection_id, item_id):
    print(f"[DEBUG] Deleting item_id: {item_id} from collection_id: {collection_id}")

    query = """
    DELETE FROM collection_items WHERE collection_id = :collection_id AND id = :item_id
    """
    db.session.execute(query, {'collection_id': collection_id, 'item_id': item_id})
    db.session.commit()

    print(f"[DEBUG] Item deleted: {item_id} from collection_id: {collection_id}")
    return jsonify({'message': 'Item deleted successfully'}), 200


# getting collections for another user
@profile_bp.route('/<int:user_id>/collections', methods=['OPTIONS', 'GET'])
@jwt_required()
def get_collections_by_user(user_id):
    if request.method == 'OPTIONS':
        return '', 204  # Return HTTP 204 No Content for preflight
    # Handle GET request as usual
    try:
        print('getting collections for user id = ', user_id)
        query = "SELECT id, name FROM collections WHERE user_id = :user_id"
        collections = db.session.execute(query, {'user_id': user_id}).fetchall()
        collections_data = [{'id': col[0], 'name': col[1]} for col in collections]
        return jsonify(collections_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch collections for the user.'}), 500
    @profile_bp.route('/verify', methods=['POST'])
@jwt_required()
def verify_profile():
    return jsonify({'message': 'Profile verification requested.'}), 200

@profile_bp.route('/deactivate', methods=['POST'])
@jwt_required()
def deactivate_profile():
    return jsonify({'message': 'Profile deactivated.'}), 200

@profile_bp.route('/reactivate', methods=['POST'])
@jwt_required()
def reactivate_profile():
    return jsonify({'message': 'Profile reactivated.'}), 200

@profile_bp.route('/download_data', methods=['GET'])
@jwt_required()
def download_profile_data():
    return jsonify({'message': 'Profile data download started.'}), 200

@profile_bp.route('/privacy_settings', methods=['GET'])
@jwt_required()
def get_privacy_settings():
    return jsonify({'privacy_settings': {}}), 200

@profile_bp.route('/privacy_settings', methods=['PUT'])
@jwt_required()
def update_privacy_settings():
    return jsonify({'message': 'Privacy settings updated.'}), 200

@profile_bp.route('/notification_settings', methods=['GET'])
@jwt_required()
def get_notification_settings():
    return jsonify({'notification_settings': {}}), 200

@profile_bp.route('/notification_settings', methods=['PUT'])
@jwt_required()
def update_notification_settings():
    return jsonify({'message': 'Notification settings updated.'}), 200

@profile_bp.route('/activity_log', methods=['GET'])
@jwt_required()
def get_activity_log():
    return jsonify({'activity_log': []}), 200

@profile_bp.route('/change_password', methods=['POST'])
@jwt_required()
def change_password():
    return jsonify({'message': 'Password changed.'}), 200

@profile_bp.route('/set_status', methods=['POST'])
@jwt_required()
def set_status():
    return jsonify({'message': 'Status set.'}), 200

@profile_bp.route('/get_status', methods=['GET'])
@jwt_required()
def get_status():
    return jsonify({'status': 'active'}), 200

@profile_bp.route('/profile_views', methods=['GET'])
@jwt_required()
def get_profile_views():
    return jsonify({'views': 0}), 200

@profile_bp.route('/block_user/<int:user_id>', methods=['POST'])
@jwt_required()
def block_user(user_id):
    return jsonify({'message': 'User blocked.'}), 200

@profile_bp.route('/unblock_user/<int:user_id>', methods=['POST'])
@jwt_required()
def unblock_user(user_id):
    return jsonify({'message': 'User unblocked.'}), 200

@profile_bp.route('/blocked_users', methods=['GET'])
@jwt_required()
def blocked_users():
    return jsonify({'blocked_users': []}), 200

@profile_bp.route('/profile_theme', methods=['PUT'])
@jwt_required()
def update_profile_theme():
    return jsonify({'message': 'Profile theme updated.'}), 200

@profile_bp.route('/profile_theme', methods=['GET'])
@jwt_required()
def get_profile_theme():
    return jsonify({'theme': 'default'}), 200

@profile_bp.route('/delete_account', methods=['DELETE'])
@jwt_required()
def delete_account():
    return jsonify({'message': 'Account deleted.'}), 200

@profile_bp.route('/request_data_removal', methods=['POST'])
@jwt_required()
def request_data_removal():
    return jsonify({'message': 'Data removal requested.'}), 200

@profile_bp.route('/add_social_link', methods=['POST'])
@jwt_required()
def add_social_link():
    return jsonify({'message': 'Social link added.'}), 200

@profile_bp.route('/remove_social_link', methods=['POST'])
@jwt_required()
def remove_social_link():
    return jsonify({'message': 'Social link removed.'}), 200

@profile_bp.route('/get_social_links', methods=['GET'])
@jwt_required()
def get_social_links():
    return jsonify({'social_links': []}), 200

@profile_bp.route('/set_profile_visibility', methods=['POST'])
@jwt_required()
def set_profile_visibility():
    return jsonify({'message': 'Profile visibility updated.'}), 200

@profile_bp.route('/get_profile_visibility', methods=['GET'])
@jwt_required()
def get_profile_visibility():
    return jsonify({'visibility': 'public'}), 200

@profile_bp.route('/add_language', methods=['POST'])
@jwt_required()
def add_language():
    return jsonify({'message': 'Language added.'}), 200

@profile_bp.route('/remove_language', methods=['POST'])
@jwt_required()
def remove_language():
    return jsonify({'message': 'Language removed.'}), 200

@profile_bp.route('/get_languages', methods=['GET'])
@jwt_required()
def get_languages():
    return jsonify({'languages': []}), 200

@profile_bp.route('/add_skill', methods=['POST'])
@jwt_required()
def add_skill():
    return jsonify({'message': 'Skill added.'}), 200

@profile_bp.route('/remove_skill', methods=['POST'])
@jwt_required()
def remove_skill():
    return jsonify({'message': 'Skill removed.'}), 200

@profile_bp.route('/get_skills', methods=['GET'])
@jwt_required()
def get_skills():
    return jsonify({'skills': []}), 200

@profile_bp.route('/add_experience', methods=['POST'])
@jwt_required()
def add_experience():
    return jsonify({'message': 'Experience added.'}), 200

@profile_bp.route('/remove_experience', methods=['POST'])
@jwt_required()
def remove_experience():
    return jsonify({'message': 'Experience removed.'}), 200

@profile_bp.route('/get_experiences', methods=['GET'])
@jwt_required()
def get_experiences():
    return jsonify({'experiences': []}), 200

@profile_bp.route('/add_education', methods=['POST'])
@jwt_required()
def add_education():
    return jsonify({'message': 'Education added.'}), 200

@profile_bp.route('/remove_education', methods=['POST'])
@jwt_required()
def remove_education():
    return jsonify({'message': 'Education removed.'}), 200

@profile_bp.route('/get_educations', methods=['GET'])
@jwt_required()
def get_educations():
    return jsonify({'educations': []}), 200

@profile_bp.route('/add_award', methods=['POST'])
@jwt_required()
def add_award():
    return jsonify({'message': 'Award added.'}), 200

