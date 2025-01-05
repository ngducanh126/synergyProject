First, we need to have a basic understanding of our app. Later when you open the frontend and play around it should be straight forward, but here are key features:

-   Users can register and login
    
-   Users can create and update their profile. User can create a collection and add items to a collection (an item can be image/video for now)
    
-   Users can go to “match” and start swiping left or right to match with others. As you swipe, you can view info about the other user.
    
-   Alternatively, a user can go to “view creators” to see all other users.
    
-   User can create a “collaboration”, which is a group of people. Let’s say user A creates a collaboration, they can name it, give it a description, set a profile picture (basic stuffs for now). Initially the collaboration only has the user A as a member. Now user B, after loggin in, can go to see many collaborations and see the collaboration user A just created. User B can request to join. Back in user A, user A can go to the “manage collaboration” page and decide to accept/reject user’s B request. If accepted, user B is now in that collaboration, and they can also start matching with people only in that collaboration
    

  

Now here are instructions set things up. In the future, we might want Docker to make CI/CD process smoother. But for now you can follow these instructions.

  

## 1. Database

  

First, create a database with postgresql. (this is the general outline, if you are not familiar with postgreSQL and pgadmin, you can look up a 20 minute tutorial on youtube. Being familiar with postgres is important for this project)

  

Open pgAdmin: Launch pgAdmin from your system.

  

**Connect to the Server:**

In the left panel, click on your PostgreSQL server (e.g., PostgreSQL 15).

Enter your password if prompted.

  

**Navigate to Databases:**

Expand the server node by clicking the arrow next to it.

Right-click on the Databases node and select Create > Database.

  

**Create the Database:**

In the dialog box, set the following:

Database Name: synergy

Owner: postgres (or your PostgreSQL username)

Click Save.

  

**Verify the Database:**

Expand the Databases node to ensure synergy appears in the list.

Now the synergy database is ready to use on port 5432.

  

### Create the tables:  
  copy this command to create the tables in pgadmin. We can have a python script in the app going forward to make things easier.
	
	-- 1. users Table

	CREATE TABLE users (

	id SERIAL PRIMARY KEY,

	username VARCHAR(255) UNIQUE NOT NULL,

	password_hash TEXT NOT NULL,

	likes INTEGER[] DEFAULT '{}',

	bio VARCHAR(255),

	skills TEXT[],

	location VARCHAR(255),

	availability VARCHAR(255),

	swipe_right INTEGER[] DEFAULT '{}',

	swipe_left INTEGER[] DEFAULT '{}',

	matches INTEGER[] DEFAULT '{}',

	preferred_medium TEXT[],

	last_active TIMESTAMP,

	verification_status BOOLEAN DEFAULT FALSE,

	profile_picture VARCHAR(255)

	);

	  

	-- 2. collaborations Table

	CREATE TABLE collaborations (

	id SERIAL PRIMARY KEY,

	admin_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

	name VARCHAR(255) NOT NULL,

	description TEXT,

	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

	profile_picture VARCHAR(255)

	);

	  

	-- 3. user_collaborations Table

	CREATE TABLE user_collaborations (

	id SERIAL PRIMARY KEY,

	user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

	collaboration_id INTEGER NOT NULL REFERENCES collaborations(id) ON DELETE CASCADE,

	role VARCHAR(50) DEFAULT 'member'

	);

	  

	-- 4. collaboration_photos Table

	-- Note: This table is not being used as of now.

	CREATE TABLE collaboration_photos (

	id SERIAL PRIMARY KEY,

	collaboration_id INTEGER NOT NULL REFERENCES collaborations(id) ON DELETE CASCADE,

	photo_path VARCHAR(255) NOT NULL

	);

	  
	  
	  

	-- 5. collections Table

	CREATE TABLE collections (

	id SERIAL PRIMARY KEY,

	user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

	name VARCHAR(255) NOT NULL,

	file_path VARCHAR(255)

	);

	  

	-- 6. collection_items Table

	CREATE TABLE collection_items (

	id SERIAL PRIMARY KEY,

	collection_id INTEGER NOT NULL REFERENCES collections(id) ON DELETE CASCADE,

	type VARCHAR(50) NOT NULL,

	content TEXT,

	file_path TEXT

	);

	  
	  

	-- 7. collaboration_requests Table

	CREATE TABLE collaboration_requests (

	id SERIAL PRIMARY KEY,

	user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

	collaboration_id INTEGER NOT NULL REFERENCES collaborations(id) ON DELETE CASCADE,

	status VARCHAR(50) NOT NULL DEFAULT 'pending',

	created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

	);

	  

	-- 8. matches Table

	CREATE TABLE matches (

	id SERIAL PRIMARY KEY,

	user1_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

	user2_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

	matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

	CONSTRAINT unique_match UNIQUE(user1_id, user2_id)

	);

	  

	-- 9. chats Table

	CREATE TABLE chats (

	id SERIAL PRIMARY KEY,

	sender_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

	receiver_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,

	message TEXT NOT NULL,

	sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP

	);

  
  

  
  

## 2. Backend

Now clone the repository to your local machine (this is stored on my personal repo but we should move it to our group repo soon) :

	git clone https://github.com/ngducanh126/synergyProject.git

  

Make sure you have Python install. You can check by running:

  
	
	python --version

  

If this returns an error, you have not installed Python. Please install it.

  

Create a file called .env in the root directory with the following content (this file is in .gitignore, so you must create the file yourself):

	  
	FLASK_ENV=development

	SECRET_KEY=your_secret_key

	DATABASE_URL=postgresql://postgres:yourpassword@127.0.0.1:5432/synergy

	BASE_URL=http://localhost:5000

	CORS_ORIGINS=http://localhost:3000

	STORAGE_METHOD=local

	UPLOAD_FOLDER_PROFILE=uploads/users

	UPLOAD_FOLDER_COLLABORATIONS=uploads/collaborations

	UPLOAD_ITEM_COLLECTION=uploads/collections

  

  
Navigate to synergyProject and create a virtual environment:

  

	python -m venv venv

  

Activate the virtual environment:

  
	
	Windows: venv\Scripts\activate

  

	macOS/Linux: source venv/bin/activate

  


  

Once in this venv, run:

	pip install -r requirements.txt

  

Now, run the local development:

  

	python run.py

  

Instructions to run the production environment will be covered later as I am still fixing and setting up stuffs.

  

The major part of the code are in app folder:

	auth_routes.py: code to handle register and login

	chat_routes.py: code to enable users to chat

	collaboration_routes: code to handle user creating a collab, requesting to join a collab, etc

	match_routes: code to handle user matching with each other

	profile_routes: code to update profile, view profile, add a collection, add items to collection, etc

## Frontend:

Clone the Repository: Open your terminal and execute:

	git clone https://github.com/ngducanh126/synergyProjectFrontend.git

  

Navigate into the project directory:

	cd synergyProjectFrontend

  

Install Dependencies: Ensure you have Node.js installed. Then, install the necessary packages:

	npm install

Start the Development Server: Launch the application using:

	npm start

You should be able to access your frontend at  http://localhost:3000/.  Make sure the backend is running and you can play around with stuffs and see new things being populated on the database.
