# WebClerk Architecture Fundamentals

How do we confirm WebClerk architecture rules and make sure they are in the ai notes so they stick between sessions:


1. CoreModel for all tables.
2. BaseModel for all tables except “pending”
3. ⁠uuid is only for cross database uses. id is used by the local database for uniqueness.
4. ⁠ida is a string value of the id. It is to make human readable id’s in the future with database id’s get too large to easily read.
5. ⁠wcapi/save is a Celery sandwitch. Check for and it it exists, run a pre-save user defined function. Save the record. Check for and if it exists, run a post-save user-defined function.