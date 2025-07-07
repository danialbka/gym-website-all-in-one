# Database Schema Update for Login Feature

## Important: Schema Changes Required

The login feature has been updated to include proper password authentication and additional user fields. You need to update your database schema to use the new login system.

## For New Installations

If you're setting up the database for the first time:

1. Run the updated `schema.sql` file in your Neon database console
2. This will create the new users table with all required fields

## For Existing Installations

If you already have a database with the old schema:

### Option 1: Run Migration Script (Recommended)
1. Run the `migration.sql` file in your Neon database console
2. This will add the new columns to your existing users table
3. **WARNING**: This sets a default password 'password123' for existing users
4. Existing users will need to register again or you'll need to implement password reset

### Option 2: Fresh Start
1. **BACKUP YOUR DATA FIRST** if you have important records
2. Drop the existing tables: `DROP TABLE prs CASCADE; DROP TABLE users CASCADE;`
3. Run the new `schema.sql` file

## New Database Schema

The updated users table now includes:
- `password_hash` - Securely hashed passwords using bcrypt
- `email` - Optional email field for account recovery
- `display_name` - Separate from username for better UX
- `is_active` - Enable/disable accounts
- `last_login` - Track user activity

## Security Notes

- Passwords are now properly hashed using bcrypt
- The default demo passwords in the schema are for development only
- Never store plain text passwords
- Email field enables future password reset functionality

## Testing the New System

After updating your schema:
1. Try registering a new user with username, password, and country
2. Test login with the new credentials
3. Verify that user sessions persist across page refreshes

## Sample Users (for testing)

The schema includes two test users:
- Username: `Danial`, Password: `password123`
- Username: `TestUser`, Password: `password123`

**Remember to change these passwords in production!**