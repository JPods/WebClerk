#!/bin/zsh
# runs the project. We 
# Enable debug mode to trace execution
set -x

# Function to execute command and show status without exiting
execute_command() {
    local cmd="$1"
    local msg="$2"
    echo "Executing: $msg..."
    if eval "$cmd"; then
        echo "SUCCESS: $msg"
    else
        echo "FAIL: $msg (Exit code: $?)"
        echo "Error details: $!"
    fi
}

# Start supporting services (Redis, Celery, etc.)
if [[ -f "./start.sh" ]]; then
    echo "Executing: Starting supporting services via start.sh..."
    ./start.sh
else
    echo "WARNING: start.sh not found, skipping service startup."
fi


# Special function for deactivate to handle shell function without exiting
deactivate_safe() {
    echo "Executing: Deactivating virtual environment..."
    if [[ -n "$VIRTUAL_ENV" ]]; then
        echo "Virtual environment detected: $VIRTUAL_ENV"
        if command -v deactivate >/dev/null 2>&1; then
            deactivate 2>/dev/null
            if [[ $? -eq 0 ]]; then
                echo "SUCCESS: Deactivating virtual environment"
            else
                echo "FAIL: Deactivating virtual environment (Exit code: $?)"
                echo "Error details: $!"
            fi
        else
            echo "WARNING: deactivate command not found, skipping deactivation"
        fi
    else
        echo "No virtual environment active, skipping deactivation"
    fi
}

# Function to create superuser using a separate Python script
create_superuser() {
    echo "Executing: Creating superuser..."

    # Run the Python script and capture output
    local output
    output=$(python create_superuser.py 2>&1)
    local exit_code=$?
    echo "$output"
    if [[ $exit_code -eq 0 ]]; then
        echo "SUCCESS: Creating superuser"
    else
        echo "FAIL: Creating superuser (Exit code: $exit_code)"
        echo "Error details: $output"
    fi
}

# Check if script is running in a valid directory
if [[ ! -f "./manage.py" ]]; then
    echo "ERROR: manage.py not found in current directory. Are you in the correct Django project directory?"
else
    echo "SUCCESS: manage.py found in current directory"
fi

# Check if virtual environment exists
if [[ ! -f "./bin/activate" ]]; then
    echo "ERROR: Virtual environment (./bin/activate) not found. Please set up a virtual environment."
else
    echo "SUCCESS: Virtual environment (./bin/activate) found"
fi

# Prompt user for choice
echo "Do you want to reset the database and start over? (y/n)"
read -r choice

# Get current username for psql
username=$(whoami)
if [[ -z "$username" ]]; then
    echo "ERROR: Could not determine current username for psql."
else
    echo "SUCCESS: Current username for psql: $username"
fi

# Check if psql is installed
if ! command -v psql >/dev/null 2>&1; then
    echo "ERROR: psql command not found. Please ensure PostgreSQL is installed."
else
    echo "SUCCESS: psql command found"
fi



if [[ "$choice" == "y" || "$choice" == "Y" ]]; then
    # Reset database and start over
    deactivate_safe
    execute_command "source ./bin/activate" "Activating virtual environment"
    execute_command "rm -f */migrations/0*.py" "Removing old migration files"
    execute_command "psql -U $username -d postgres -c \"SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'commerce_expert' AND pid <> pg_backend_pid();\"" "Terminating active connections to commerce_expert database"
    execute_command "psql -U $username -d postgres -c \"DROP DATABASE IF EXISTS commerce_expert;\"" "Dropping commerce_expert database"
    execute_command "psql -U $username -d postgres -c \"CREATE DATABASE commerce_expert;\"" "Creating commerce_expert database"
    execute_command "python manage.py makemigrations" "Creating new migrations"
    execute_command "python manage.py migrate" "Applying migrations"
    create_superuser
    execute_command "python manage.py runserver" "Starting Django server"
else
    # Just run the server
    deactivate_safe
    execute_command "source ./bin/activate" "Activating virtual environment"
    execute_command "python manage.py makemigrations" "Creating new migrations"
    execute_command "python manage.py migrate" "Applying migrations"
    execute_command "python manage.py runserver" "Starting Django server"
fi



# Disable debug mode
set +x

echo "Script completed execution of all commands."