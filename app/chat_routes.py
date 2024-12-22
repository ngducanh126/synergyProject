from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from app import db, socketio
from flask_socketio import emit, join_room, leave_room

chat_bp = Blueprint('chat', __name__)

# Route to fetch chat history
@chat_bp.route('/history/<int:receiver_id>', methods=['GET'])
@jwt_required()
def get_chat_history(receiver_id):
    sender_id = get_jwt_identity()
    print(f"[DEBUG] Fetching chat history: sender_id={sender_id}, receiver_id={receiver_id}")

    # Fetch chat history between sender_id and receiver_id
    chat_history_query = """
    SELECT sender_id, message, timestamp
    FROM chats
    WHERE (sender_id = :sender_id AND receiver_id = :receiver_id)
       OR (sender_id = :receiver_id AND receiver_id = :sender_id)
    ORDER BY timestamp;
    """
    messages = db.session.execute(chat_history_query, {'sender_id': sender_id, 'receiver_id': receiver_id}).fetchall()

    chat_history = [
        {'sender_id': msg[0], 'message': msg[1], 'timestamp': msg[2].isoformat()}
        for msg in messages
    ]

    print(f"[DEBUG] Retrieved chat history: {chat_history}")
    return jsonify(chat_history), 200

# WebSocket events for real-time messaging
@socketio.on('join')
def handle_join(data):
    room = data['room']
    print(f"[DEBUG] Joining room: {room}")
    join_room(room)
    emit('status', {'message': f"User joined room: {room}"}, room=room)


@socketio.on('leave')
def handle_leave(data):
    room = data['room']
    user_id = get_jwt_identity()
    print(f"[DEBUG] User {user_id} is attempting to leave room: {room}")
    leave_room(room)
    print(f"[DEBUG] User {user_id} successfully left room: {room}")
    emit('status', {'message': f"User {user_id} has left the room."}, room=room)


@socketio.on('message')
def handle_message(data):
    sender_id = data['sender_id']
    receiver_id = data['receiver_id']
    room = data['room']
    message = data['message']

    print(f"[DEBUG] Received message from sender_id: {sender_id} to receiver_id: {receiver_id}")
    print(f"[DEBUG] Room: {room}")
    print(f"[DEBUG] Message content: {message}")

    # Save message to the database
    insert_query = """
    INSERT INTO chats (sender_id, receiver_id, message)
    VALUES (:sender_id, :receiver_id, :message);
    """
    try:
        db.session.execute(insert_query, {'sender_id': sender_id, 'receiver_id': receiver_id, 'message': message})
        db.session.commit()
        print(f"[DEBUG] Message saved to database from {sender_id} to {receiver_id}")
    except Exception as e:
        print(f"[ERROR] Failed to save message to database: {e}")

    # Emit the message to the room
    emit('message', {
        'sender_id': sender_id,
        'receiver_id': receiver_id,
        'message': message,
        # 'timestamp': str(datetime.now())  # Include timestamp for the message
    }, room=room)
    print(f"[DEBUG] Message broadcasted to room: {room}")
