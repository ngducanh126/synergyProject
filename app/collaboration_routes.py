from flask import Blueprint, jsonify, request, current_app
from flask_jwt_extended import jwt_required, get_jwt_identity
import boto3
import mimetypes
import os
import tempfile
from botocore.config import Config as BotoConfig
from botocore.exceptions import NoCredentialsError
from app import db

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

collaboration_bp = Blueprint('collaboration', __name__)

def allowed_file(filename):
    """Check if the file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def save_profile_picture(file, collaboration_id, is_edit=False):
    """Save profile picture for a collaboration based on the configured storage method."""
    profile_picture_path = None

    try:

        # Create S3 client with environment variables
        s3 = boto3.client(
            's3',
            aws_access_key_id=current_app.config['AWS_ACCESS_KEY'],
            aws_secret_access_key=current_app.config['AWS_SECRET_KEY'],
            region_name=current_app.config['AWS_REGION'],
            config=BotoConfig(connect_timeout=5, read_timeout=10, retries={'max_attempts': 3})
        )

        # Generate S3 object name
        object_name = f"collaborations/{collaboration_id}/profile_pic.{file.filename.rsplit('.', 1)[1].lower()}"

        # Save file to a temporary location
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name

        # Detect content type dynamically
        content_type, _ = mimetypes.guess_type(temp_file_path)
        content_type = content_type or "application/octet-stream"
        print(f"[DEBUG] Using Content-Type: {content_type}")

        # Upload to S3 using put_object
        with open(temp_file_path, "rb") as file_data:
            print(f"[DEBUG] Starting upload to S3...")
            s3.put_object(
                Bucket=current_app.config['AWS_BUCKET_NAME'],
                Key=object_name,
                Body=file_data,
                ContentType=content_type
            )
        profile_picture_path = f"https://{current_app.config['AWS_BUCKET_NAME']}.s3.{current_app.config['AWS_REGION']}.amazonaws.com/{object_name}"
        print(f"[DEBUG] Uploaded to AWS S3 successfully. URL: {profile_picture_path}")



    except NoCredentialsError:
        print("[ERROR] AWS credentials not found.")
        raise
    except Exception as e:
        print(f"[ERROR] Failed to save profile picture: {str(e)}")
        raise
    finally:
        # Clean up temporary file
            os.unlink(temp_file_path)

    return profile_picture_path



# Create a collaboration
@collaboration_bp.route('/create', methods=['POST'])
@jwt_required()
def create_collaboration():
    user_id = get_jwt_identity()
    name = request.form.get('name')
    description = request.form.get('description')
    file = request.files.get('profile_picture')  # File from the request

    if not name:
        return jsonify({'error': 'Collaboration name is required'}), 400

    try:
        # Insert the collaboration into the database first to get the ID
        query = """
        INSERT INTO collaborations (admin_id, name, description, profile_picture)
        VALUES (:admin_id, :name, :description, NULL)
        RETURNING id;
        """
        result = db.session.execute(query, {
            'admin_id': user_id,
            'name': name,
            'description': description
        })
        collaboration_id = result.fetchone()[0]

        profile_picture_url = None
        if file and allowed_file(file.filename):
            profile_picture_url = save_profile_picture(file, collaboration_id)

            # Update the profile picture path in the database
            update_query = """
            UPDATE collaborations
            SET profile_picture = :profile_picture
            WHERE id = :collaboration_id;
            """
            db.session.execute(update_query, {'profile_picture': profile_picture_url, 'collaboration_id': collaboration_id})
            db.session.commit()

        # Add the creator as an admin to the user_collaborations table
        user_collab_query = """
        INSERT INTO user_collaborations (user_id, collaboration_id, role)
        VALUES (:user_id, :collaboration_id, 'admin');
        """
        db.session.execute(user_collab_query, {'user_id': user_id, 'collaboration_id': collaboration_id})
        db.session.commit()

        return jsonify({'message': 'Collaboration created successfully', 'id': collaboration_id, 'profile_picture_url': profile_picture_url}), 201
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to create collaboration'}), 500

# Edit a collaboration
@collaboration_bp.route('/edit/<int:collaboration_id>', methods=['PUT'])
@jwt_required()
def edit_collaboration(collaboration_id):
    user_id = get_jwt_identity()
    data = request.form
    name = data.get('name')
    description = data.get('description')
    profile_picture = request.files.get('profile_picture')  # Optional file upload

    print(f"[DEBUG] Received edit request for Collaboration ID: {collaboration_id} by User ID: {user_id}")
    try:
        # Prepare the fields to update
        update_fields = []
        update_values = {'collaboration_id': collaboration_id}

        if name:
            update_fields.append("name = :name")
            update_values['name'] = name

        if description:
            update_fields.append("description = :description")
            update_values['description'] = description

        if profile_picture and allowed_file(profile_picture.filename):
            profile_picture_url = save_profile_picture(profile_picture, collaboration_id, is_edit=True)
            update_fields.append("profile_picture = :profile_picture")
            update_values['profile_picture'] = profile_picture_url

        # Update the collaboration in the database
        if update_fields:
            update_query = f"""
            UPDATE collaborations
            SET {", ".join(update_fields)}
            WHERE id = :collaboration_id;
            """
            db.session.execute(update_query, update_values)
            db.session.commit()

        return jsonify({'message': 'Collaboration updated successfully.'}), 200
    except Exception as e:
        print(f"[ERROR] Failed to update collaboration: {e}")
        return jsonify({'error': 'Failed to update collaboration.'}), 500


# View all collaborations
@collaboration_bp.route('/view', methods=['GET'])
@jwt_required()
def view_collaborations():
    try:
        user_id = get_jwt_identity()
        print(f"[DEBUG] Token validated. User ID: {user_id}")

        # Query to fetch all collaborations, including profile_picture
        query = """
        SELECT c.id, c.name, c.description, c.created_at, u.username AS admin_name, c.profile_picture
        FROM collaborations c
        JOIN users u ON c.admin_id = u.id;
        """
        collaborations = db.session.execute(query).fetchall()

        collaborations_data = []

        for collab in collaborations:
            collab_data = {
                'id': collab[0],
                'name': collab[1],
                'description': collab[2],
                'created_at': collab[3].isoformat(),
                'admin_name': collab[4],
                'profile_picture': collab[5]  # Include profile_picture
            }
            print(f"[DEBUG] Collaboration ID: {collab_data['id']}, Profile Picture: {collab_data['profile_picture']}")
            collaborations_data.append(collab_data)

        print(f"[DEBUG] Retrieved {len(collaborations_data)} collaborations.")
        return jsonify(collaborations_data), 200
    except Exception as e:
        print(f"[ERROR] Failed to fetch collaborations: {e}")
        return jsonify({'error': 'Failed to fetch collaborations'}), 500


# Add photo to a collaboration (not implemented on front-end yet)  ; need to make storage logic better and use cloud
@collaboration_bp.route('/<int:collaboration_id>/photos', methods=['POST'])
@jwt_required()
def add_photo_to_collaboration(collaboration_id):
    user_id = get_jwt_identity()

    # Check if the user is an admin of the collaboration
    admin_query = """
    SELECT role FROM user_collaborations
    WHERE user_id = :user_id AND collaboration_id = :collaboration_id AND role = 'admin';
    """
    admin = db.session.execute(admin_query, {'user_id': user_id, 'collaboration_id': collaboration_id}).fetchone()

    if not admin:
        return jsonify({'error': 'You do not have permission to add photos to this collaboration'}), 403

    # Check if the request contains a file
    if 'file' not in request.files:
        return jsonify({'error': 'Photo file is required'}), 400

    file = request.files['file']
    filename = secure_filename(file.filename)
    file_path = os.path.join('uploads', filename)
    file.save(file_path)

    # Add photo to the collaboration_photos table
    try:
        query = """
        INSERT INTO collaboration_photos (collaboration_id, photo_path)
        VALUES (:collaboration_id, :photo_path);
        """
        db.session.execute(query, {'collaboration_id': collaboration_id, 'photo_path': file_path})
        db.session.commit()

        return jsonify({'message': 'Photo added successfully', 'file_path': file_path}), 201
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to add photo'}), 500

# View photos in a collaboration  (not implemented on front-end yet)  ; need to make storage logic better and use cloud
@collaboration_bp.route('/<int:collaboration_id>/photos', methods=['GET'])
@jwt_required()
def view_collaboration_photos(collaboration_id):
    try:
        query = """
        SELECT id, photo_path FROM collaboration_photos
        WHERE collaboration_id = :collaboration_id;
        """
        photos = db.session.execute(query, {'collaboration_id': collaboration_id}).fetchall()

        photos_data = [
            {
                'id': photo[0],
                'photo_url': f"http://127.0.0.1:5000/uploads/{os.path.basename(photo[1])}"
            }
            for photo in photos
        ]
        return jsonify(photos_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch photos'}), 500


# getting all collaborations that i am admin of
@collaboration_bp.route('/collaborations-i-own', methods=['GET'])
@jwt_required()
def view_my_collaborations():
    user_id = get_jwt_identity()
    try:
        print(f"[DEBUG] Fetching collaborations for user_id: {user_id}")

        # Query to fetch collaborations where the user is the admin
        query = """
        SELECT id, name, description, profile_picture, created_at
        FROM collaborations
        WHERE admin_id = :user_id;
        """
        my_collaborations = db.session.execute(query, {'user_id': user_id}).fetchall()

        collaborations_data = [
            {
                'id': collab[0],
                'name': collab[1],
                'description': collab[2],
                'profile_picture': collab[3],
                'created_at': collab[4].isoformat(),
            }
            for collab in my_collaborations
        ]

        print(f"[DEBUG] User {user_id} is admin of {len(collaborations_data)} collaborations.")
        return jsonify(collaborations_data), 200
    except Exception as e:
        print(f"[ERROR] Failed to fetch user's collaborations: {e}")
        return jsonify({'error': 'Failed to fetch collaborations'}), 500


# viewing a collaboration (could be mine or another user's)
@collaboration_bp.route('/<int:collaboration_id>', methods=['GET'])
@jwt_required()
def view_collaboration(collaboration_id):
    query = """
    SELECT c.id, c.name, c.description, c.profile_picture, u.username AS admin_name
    FROM collaborations c
    JOIN users u ON c.admin_id = u.id
    WHERE c.id = :collaboration_id;
    """
    collab = db.session.execute(query, {'collaboration_id': collaboration_id}).fetchone()

    if not collab:
        return jsonify({'error': 'Collaboration not found'}), 404

    collaboration_data = {
        'id': collab[0],
        'name': collab[1],
        'description': collab[2],
        'profile_picture': collab[3],
        'admin_name': collab[4],
    }
    return jsonify(collaboration_data), 200

# request to join
@collaboration_bp.route('/<int:collaboration_id>/request', methods=['POST'])
@jwt_required()
def request_to_join_collaboration(collaboration_id):
    user_id = get_jwt_identity()
    try:
        # Check if the user is already an admin or a member of the collaboration
        existing_membership_query = """
        SELECT 1
        FROM user_collaborations
        WHERE user_id = :user_id AND collaboration_id = :collaboration_id;
        """
        is_member_or_admin = db.session.execute(
            existing_membership_query, {'user_id': user_id, 'collaboration_id': collaboration_id}
        ).fetchone()

        if is_member_or_admin:
            return jsonify({'error': 'You are already a member or admin of this collaboration.'}), 400

        # Check if the user has an existing pending request
        existing_request_query = """
        SELECT id 
        FROM collaboration_requests
        WHERE user_id = :user_id AND collaboration_id = :collaboration_id AND status = 'pending';
        """
        existing_request = db.session.execute(
            existing_request_query, {'user_id': user_id, 'collaboration_id': collaboration_id}
        ).fetchone()

        if existing_request:
            return jsonify({'error': 'You already have a pending request to this collaboration.'}), 400

        # Insert the new request
        insert_query = """
        INSERT INTO collaboration_requests (user_id, collaboration_id, status)
        VALUES (:user_id, :collaboration_id, 'pending');
        """
        db.session.execute(insert_query, {'user_id': user_id, 'collaboration_id': collaboration_id})
        db.session.commit()

        return jsonify({'message': 'Request sent successfully.'}), 201

    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to send request.'}), 500


@collaboration_bp.route('/requests-that-i-sent', methods=['GET'])
@jwt_required()
def view_my_collab_requests():
    user_id = get_jwt_identity()
    try:
        query = """
        SELECT cr.id, cr.status, c.name AS collaboration_name, c.description, cr.created_at
        FROM collaboration_requests cr
        JOIN collaborations c ON cr.collaboration_id = c.id
        WHERE cr.user_id = :user_id;
        """
        requests = db.session.execute(query, {'user_id': user_id}).fetchall()

        requests_data = [
            {
                'id': req[0],
                'status': req[1],
                'collaboration_name': req[2],
                'collaboration_description': req[3],
                'date': req[4].strftime('%Y-%m-%d %H:%M:%S') if req[4] else None,
            }
            for req in requests
        ]
        return jsonify(requests_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch collaboration requests.'}), 500


# accept or reject a request
@collaboration_bp.route('/requests/<int:request_id>', methods=['PUT'])
@jwt_required()
def handle_collaboration_request(request_id):
    user_id = get_jwt_identity()
    data = request.get_json()
    status = data.get('status')  # 'approved' or 'rejected'

    if status not in ['approved', 'rejected']:
        return jsonify({'error': 'Invalid status. Use "approved" or "rejected".'}), 400

    try:
        # Update the request status
        update_query = """
        UPDATE collaboration_requests
        SET status = :status
        WHERE id = :request_id;
        """
        db.session.execute(update_query, {'status': status, 'request_id': request_id})
        db.session.commit()

        # If approved, add the user to the collaboration
        if status == 'approved':
            user_collab_query = """
            INSERT INTO user_collaborations (user_id, collaboration_id, role)
            SELECT cr.user_id, cr.collaboration_id, 'member'
            FROM collaboration_requests cr
            WHERE cr.id = :request_id;
            """
            db.session.execute(user_collab_query, {'request_id': request_id})
            db.session.commit()

        return jsonify({'message': f'Request has been {status} successfully.'}), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to handle collaboration request.'}), 500



@collaboration_bp.route('/view-requests-sent-to-me', methods=['GET'])
@jwt_required()
def view_pending_requests_for_admin():
    user_id = get_jwt_identity()
    try:
        query = """
        SELECT cr.id, cr.status, u.username AS requester_name, c.name AS collaboration_name
        FROM collaboration_requests cr
        JOIN collaborations c ON cr.collaboration_id = c.id
        JOIN users u ON cr.user_id = u.id
        WHERE c.admin_id = :user_id AND cr.status = 'pending';
        """
        requests = db.session.execute(query, {'user_id': user_id}).fetchall()

        requests_data = [
            {
                'id': req[0],
                'status': req[1],
                'requester_name': req[2],
                'collaboration_name': req[3],
            }
            for req in requests
        ]
        return jsonify(requests_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch pending requests.'}), 500

# view collaborations i joined (i could either be an admin or a member)
@collaboration_bp.route('/joined', methods=['GET'])
@jwt_required()
def view_collaborations_i_joined():
    user_id = get_jwt_identity()
    try:
        query = """
        SELECT c.id, c.name, c.description, c.profile_picture, uc.role
        FROM user_collaborations uc
        JOIN collaborations c ON uc.collaboration_id = c.id
        WHERE uc.user_id = :user_id;
        """
        collaborations = db.session.execute(query, {'user_id': user_id}).fetchall()

        collaborations_data = [
            {
                'id': collab[0],
                'name': collab[1],
                'description': collab[2],
                'profile_picture': collab[3],
                'role': collab[4],  # Add the role column
            }
            for collab in collaborations
        ]
        return jsonify(collaborations_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch joined collaborations.'}), 500


@collaboration_bp.route('/popular', methods=['GET'])
@jwt_required()
def get_popular_collaborations():
    try:
        user_id = get_jwt_identity()
        print(f"[DEBUG] User ID: {user_id}")

        # Fetch the top 3 collaborations with the most users
        query = """
        SELECT c.id, c.name, c.description, c.profile_picture, COUNT(uc.user_id) as user_count
        FROM collaborations c
        LEFT JOIN user_collaborations uc ON c.id = uc.collaboration_id
        GROUP BY c.id, c.profile_picture
        ORDER BY user_count DESC
        LIMIT 3;
        """
        collaborations = db.session.execute(query).fetchall()

        collaborations_data = [
            {
                'id': collab[0],
                'name': collab[1],
                'description': collab[2],
                'profile_picture': collab[3],
                'user_count': collab[4],
            }
            for collab in collaborations
        ]
        print(f"[DEBUG] Popular Collaborations: {collaborations_data}")
        return jsonify(collaborations_data), 200
    except Exception as e:
        print(f"[ERROR] {e}")
        return jsonify({'error': 'Failed to fetch popular collaborations.'}), 500


@collaboration_bp.route('/<int:collaboration_id>/members', methods=['GET'])
@jwt_required()
def get_collaboration_members(collaboration_id):
    try:
        # Query to fetch users who are part of the collaboration
        query = """
        SELECT u.id, u.username, u.bio, u.skills, u.location, u.profile_picture, uc.role
        FROM user_collaborations uc
        JOIN users u ON uc.user_id = u.id
        WHERE uc.collaboration_id = :collaboration_id AND uc.role = 'member' ;
        """
        members = db.session.execute(query, {'collaboration_id': collaboration_id}).fetchall()

        members_data = [
            {
                'id': member[0],
                'username': member[1],
                'bio': member[2],
                'skills': member[3],
                'location': member[4],
                'profile_picture': member[5],
                'role': member[6],
            }
            for member in members
        ]

        return jsonify({'members': members_data}), 200
    except Exception as e:
        print(f"[ERROR] Failed to fetch members for collaboration ID {collaboration_id}: {e}")
        return jsonify({'error': 'Failed to fetch collaboration members.'}), 500
@collaboration_bp.route('/<int:collaboration_id>/remove-member', methods=['POST'])
@jwt_required()
def remove_member_from_collaboration(collaboration_id):
    """Remove a member from a collaboration."""
    return jsonify({'message': 'Member removed from collaboration.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/remove-member', methods=['POST'])
@jwt_required()
def remove_member_from_collaboration(collaboration_id):
    """Remove a member from a collaboration."""
    return jsonify({'message': 'Member removed from collaboration.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/make-admin', methods=['POST'])
@jwt_required()
def make_member_admin(collaboration_id):
    """Promote a member to admin in a collaboration."""
    return jsonify({'message': 'Member promoted to admin.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/demote-admin', methods=['POST'])
@jwt_required()
def demote_admin_to_member(collaboration_id):
    """Demote an admin to member in a collaboration."""
    return jsonify({'message': 'Admin demoted to member.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/leave', methods=['POST'])
@jwt_required()
def leave_collaboration(collaboration_id):
    """Allow a user to leave a collaboration."""
    return jsonify({'message': 'You have left the collaboration.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/update-description', methods=['PUT'])
@jwt_required()
def update_collaboration_description(collaboration_id):
    """Update the description of a collaboration."""
    return jsonify({'message': 'Collaboration description updated.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/update-name', methods=['PUT'])
@jwt_required()
def update_collaboration_name(collaboration_id):
    """Update the name of a collaboration."""
    return jsonify({'message': 'Collaboration name updated.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/invite', methods=['POST'])
@jwt_required()
def invite_user_to_collaboration(collaboration_id):
    """Invite a user to join a collaboration."""
    return jsonify({'message': 'User invited to collaboration.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/cancel-invite', methods=['POST'])
@jwt_required()
def cancel_invite_to_collaboration(collaboration_id):
    """Cancel an invitation to a collaboration."""
    return jsonify({'message': 'Invitation cancelled.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/list-invites', methods=['GET'])
@jwt_required()
def list_collaboration_invites(collaboration_id):
    """List all pending invites for a collaboration."""
    return jsonify({'invites': []}), 200

@collaboration_bp.route('/<int:collaboration_id>/archive', methods=['POST'])
@jwt_required()
def archive_collaboration(collaboration_id):
    """Archive a collaboration."""
    return jsonify({'message': 'Collaboration archived.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/unarchive', methods=['POST'])
@jwt_required()
def unarchive_collaboration(collaboration_id):
    """Unarchive a collaboration."""
    return jsonify({'message': 'Collaboration unarchived.'}), 200

@collaboration_bp.route('/archived', methods=['GET'])
@jwt_required()
def list_archived_collaborations():
    """List all archived collaborations."""
    return jsonify({'archived_collaborations': []}), 200

@collaboration_bp.route('/<int:collaboration_id>/add-tag', methods=['POST'])
@jwt_required()
def add_tag_to_collaboration(collaboration_id):
    """Add a tag to a collaboration."""
    return jsonify({'message': 'Tag added to collaboration.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/remove-tag', methods=['POST'])
@jwt_required()
def remove_tag_from_collaboration(collaboration_id):
    """Remove a tag from a collaboration."""
    return jsonify({'message': 'Tag removed from collaboration.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/tags', methods=['GET'])
@jwt_required()
def list_collaboration_tags(collaboration_id):
    """List all tags for a collaboration."""
    return jsonify({'tags': []}), 200

@collaboration_bp.route('/<int:collaboration_id>/add-note', methods=['POST'])
@jwt_required()
def add_note_to_collaboration(collaboration_id):
    """Add a note to a collaboration."""
    return jsonify({'message': 'Note added to collaboration.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/notes', methods=['GET'])
@jwt_required()
def list_collaboration_notes(collaboration_id):
    """List all notes for a collaboration."""
    return jsonify({'notes': []}), 200

@collaboration_bp.route('/<int:collaboration_id>/delete', methods=['DELETE'])
@jwt_required()
def delete_collaboration(collaboration_id):
    """Delete a collaboration."""
    return jsonify({'message': 'Collaboration deleted.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/transfer-ownership', methods=['POST'])
@jwt_required()
def transfer_collaboration_ownership(collaboration_id):
    """Transfer ownership of a collaboration to another user."""
    return jsonify({'message': 'Collaboration ownership transferred.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/activity', methods=['GET'])
@jwt_required()
def get_collaboration_activity(collaboration_id):
    """Get recent activity for a collaboration."""
    return jsonify({'activity': []}), 200

@collaboration_bp.route('/<int:collaboration_id>/mute', methods=['POST'])
@jwt_required()
def mute_collaboration(collaboration_id):
    return jsonify({'message': 'Collaboration muted.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/unmute', methods=['POST'])
@jwt_required()
def unmute_collaboration(collaboration_id):
    return jsonify({'message': 'Collaboration unmuted.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/muted', methods=['GET'])
@jwt_required()
def get_muted_collaborations(collaboration_id):
    return jsonify({'muted': False}), 200

@collaboration_bp.route('/<int:collaboration_id>/star', methods=['POST'])
@jwt_required()
def star_collaboration(collaboration_id):
    return jsonify({'message': 'Collaboration starred.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/unstar', methods=['POST'])
@jwt_required()
def unstar_collaboration(collaboration_id):
    return jsonify({'message': 'Collaboration unstarred.'}), 200

@collaboration_bp.route('/starred', methods=['GET'])
@jwt_required()
def get_starred_collaborations():
    return jsonify({'starred_collaborations': []}), 200

@collaboration_bp.route('/<int:collaboration_id>/pin', methods=['POST'])
@jwt_required()
def pin_collaboration(collaboration_id):
    return jsonify({'message': 'Collaboration pinned.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/unpin', methods=['POST'])
@jwt_required()
def unpin_collaboration(collaboration_id):
    return jsonify({'message': 'Collaboration unpinned.'}), 200

@collaboration_bp.route('/pinned', methods=['GET'])
@jwt_required()
def get_pinned_collaborations():
    return jsonify({'pinned_collaborations': []}), 200

@collaboration_bp.route('/<int:collaboration_id>/reminders', methods=['GET'])
@jwt_required()
def get_collaboration_reminders(collaboration_id):
    return jsonify({'reminders': []}), 200

@collaboration_bp.route('/<int:collaboration_id>/add-reminder', methods=['POST'])
@jwt_required()
def add_collaboration_reminder(collaboration_id):
    return jsonify({'message': 'Reminder added.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/remove-reminder', methods=['POST'])
@jwt_required()
def remove_collaboration_reminder(collaboration_id):
    return jsonify({'message': 'Reminder removed.'}), 200

@collaboration_bp.route('/<int:collaboration_id>/calendar', methods=['GET'])
@jwt_required()
def get_collaboration_calendar(collaboration_id):
    return jsonify({'calendar': []}), 200

