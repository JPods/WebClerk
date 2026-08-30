Lets add to our documentation and instructions that there are 4 indentifiers associated with each transaction line:
1 and 2: id and ida are unique to each line but do not exist until the line is saved. 
3. line_number is unique to each in each parent transaction and is set by the parent.line_increment. This is used to control uniqueness in the React frontend before the line is saved. It can be used by the frontend and backend as the source of truth so if it is limited to use within the transaction. This simplifies software behaviors to have only one source of truth.
4. sequence is the order the user wants lines displayed.

When lines are being created between transactions, cloned or transfer of authority over inventory, the .refs.parent.model_name, .id, .fulfilment ("dedicated" = use of inventory limited to this parent/child transaction; or "general" = applied to the general pool of inventory.) if it is benefi