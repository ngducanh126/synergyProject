from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db
import os
import cloudinary.uploader

profile_bp = Blueprint('profile', __name__)

# Define allowed extensions
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_profile_picture(file, user_id):
    """Save profile picture based on storage method."""
    # Get configuration values from the app's config
    storage_method = current_app.config['STORAGE_METHOD']
    upload_folder_profile = current_app.config['UPLOAD_FOLDER_PROFILE']
    profile_picture_path = None

    print(f"[DEBUG] Storage method: {storage_method}")
    print(f"[DEBUG] Upload folder (profile): {upload_folder_profile}")

    if storage_method == 'cloudinary':
        # Use Cloudinary to upload the profile picture
        cloudinary_folder = f"users/{user_id}"
        print(f"[DEBUG] Cloudinary folder: {cloudinary_folder}")
        upload_result = cloudinary.uploader.upload(
            file,
            folder=cloudinary_folder,
            public_id="profile_pic",  # Save as profile_pic in the user's folder
            overwrite=True,          # Replace existing profile_pic
            resource_type="image"
        )
        profile_picture_path = upload_result['secure_url']  # Use Cloudinary's secure URL
        print(f"[DEBUG] Uploaded to Cloudinary, secure URL: {profile_picture_path}")
    else:
        # Save locally
        file_extension = file.filename.rsplit('.', 1)[1].lower()
        print(f"[DEBUG] File extension: {file_extension}")
        user_folder = os.path.join(upload_folder_profile, str(user_id))
        print(f"[DEBUG] Local user folder: {user_folder}")
        os.makedirs(user_folder, exist_ok=True)
        filename = f"profile_pic.{file_extension}"
        print(f"[DEBUG] Filename: {filename}")
        file_path = os.path.join(user_folder, filename)
        print(f"[DEBUG] File path before saving: {file_path}")
        file.save(file_path)
        print(f"[DEBUG] File saved at: {file_path}")

        # Save only the relative path in the database
        profile_picture_path = os.path.join(upload_folder_profile, str(user_id), filename).replace("\\", "/")
        print(f"[DEBUG] Relative path stored in DB: {profile_picture_path}")

    return profile_picture_path



# View my profile
@profile_bp.route('/view', methods=['GET'])
@jwt_required()
def view_profile():
    user_id = get_jwt_identity()

    try:
        # Fetch current user details
        user_query = """
        SELECT id, username, bio, skills, location, availability, verification_status, profile_picture
        FROM users
        WHERE id = :user_id;
        """
        user = db.session.execute(user_query, {'user_id': user_id}).fetchone()

        if not user:
            return jsonify({'message': 'User not found'}), 404

        # Fetch collaborations where the user is a member or admin
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

    # Check if the user exists
    user_query = "SELECT id FROM users WHERE id = :user_id;"
    user = db.session.execute(user_query, {'user_id': user_id}).fetchone()

    if not user:
        return jsonify({'message': 'User not found'}), 404

    # Initialize variables
    bio = request.form.get('bio')
    skills = request.form.get('skills')  # Assume this is a comma-separated string
    location = request.form.get('location')
    availability = request.form.get('availability')
    file = request.files.get('profile_picture')

    # Handle profile picture upload
    profile_picture_path = None
    if file and allowed_file(file.filename):
        try:
            profile_picture_path = save_profile_picture(file, user_id)
        except Exception as e:
            return jsonify({'message': 'Failed to upload profile picture', 'error': str(e)}), 500

    # Convert skills to PostgreSQL array format
    if skills:
        skills = "{" + ",".join(skill.strip() for skill in skills.split(',')) + "}"

    # Update profile data in the database
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

        # Include the full URL in the response
        full_url = (
            f"{current_app.config['BASE_URL']}/{profile_picture_path}" if profile_picture_path else None
        )
        return jsonify({
            'message': 'Profile updated successfully',
            'profile_picture_url': full_url
        }), 200
    except Exception as e:
        return jsonify({'message': 'Failed to update profile', 'error': str(e)}), 500



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
    """Add an item to a collection."""
    try:
        user_id = get_jwt_identity()
        print(f"[DEBUG] User ID: {user_id}, Collection ID: {collection_id}")

        # Initialize variables
        item_type = None
        content = None
        file_path = None

        if 'file' in request.files:
            # Handle file uploads
            file = request.files.get('file')
            item_type = request.form.get('type')
            content = request.form.get('content')
            print(f"[DEBUG] Form data (file upload): Type: {item_type}, Content: {content}, File: {file.filename if file else 'None'}")

            if file:
                # Save the file locally or to Cloudinary
                storage_method = current_app.config['STORAGE_METHOD']
                upload_folder_collection = current_app.config['UPLOAD_ITEM_COLLECTION']
                print(f"[DEBUG] Storage method: {storage_method}")

                file_extension = file.filename.rsplit('.', 1)[1].lower()
                filename = f"item_{collection_id}_{user_id}.{file_extension}"
                relative_path = os.path.join(upload_folder_collection, str(collection_id), filename).replace("\\", "/")

                if storage_method == 'cloudinary':
                    cloudinary_folder = f"collections/{collection_id}"
                    print(f"[DEBUG] Cloudinary folder: {cloudinary_folder}")
                    upload_result = cloudinary.uploader.upload(
                        file,
                        folder=cloudinary_folder,
                        public_id=filename.rsplit('.', 1)[0],
                        overwrite=True,
                        resource_type="image"
                    )
                    file_path = upload_result['secure_url']
                else:
                    # Save locally
                    local_folder = os.path.join(upload_folder_collection, str(collection_id))
                    os.makedirs(local_folder, exist_ok=True)
                    full_path = os.path.join(local_folder, filename)
                    file.save(full_path)
                    file_path = relative_path
                    print(f"[DEBUG] File saved locally at: {full_path}")
            else:
                print("[DEBUG] No file uploaded.")
        else:
            # Handle JSON payloads
            data = request.get_json()
            item_type = data.get('type')
            content = data.get('content')
            print(f"[DEBUG] JSON data: Type: {item_type}, Content: {content}")

        # Ensure mandatory fields are present
        if not item_type or not content:
            print("[ERROR] Missing type or content in request")
            return jsonify({'error': 'Type and content are required fields'}), 400

        # Insert into database
        query = """
        INSERT INTO collection_items (collection_id, type, content, file_path)
        VALUES (:collection_id, :type, :content, :file_path)
        """
        db.session.execute(query, {
            'collection_id': collection_id,
            'type': item_type,
            'content': content,
            'file_path': file_path  # Store relative path or Cloudinary URL
        })
        db.session.commit()

        print(f"[DEBUG] Item added to database - Type: {item_type}, Content: {content}, File Path: {file_path}")
        return jsonify({'message': 'Item added to collection successfully', 'file_path': file_path}), 201

    except Exception as e:
        print(f"[ERROR] {e}")
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
            # Ensure the file path is normalized
            if item[3]:  # Check if file_path exists
                # Dynamically determine the base URL
                base_url = request.host_url.rstrip('/')  # Removes trailing slash
                normalized_file_path = f"{base_url}/{item[3]}"  # Prefix with base URL
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


@profile_bp.route('/uploads/<path:filename>', methods=['GET'])
def serve_upload(filename):
    try:
        upload_folder = os.path.join(os.getcwd(), 'uploads')
        file_path = os.path.join(upload_folder, filename)
        print(f"[DEBUG] File request: {filename}, Full path: {file_path}")

        if not os.path.exists(file_path):
            print(f"[ERROR] File not found at: {file_path}")
            return jsonify({'error': 'File not found'}), 404

        print(f"[DEBUG] File exists. Serving: {filename}")
        return send_from_directory(upload_folder, filename)
    except Exception as e:
        print(f"[ERROR] Failed to serve file: {filename}. Error: {e}")
        return jsonify({'error': 'File not found or inaccessible'}), 404

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
    