# Git Workflow Procedure

This document outlines the standard procedure for working with Git in this project.

## Development Workflow

1. **Pull from dev to your own branch**
   - Create or switch to your feature branch.
   - Pull the latest changes from the `dev` branch.

2. **Do work**
   - Make your code changes and commits on your branch.

3. **Push to own branch**
   - Push your commits to your remote branch.

4. **Merge with dev using pull request**
   - Create a pull request on GitHub to merge your branch into `dev`.
   - Wait for review and approval before merging.

## Git Commands to Resolve Defects

Here are common Git commands to resolve issues such as merge conflicts, reverts, or other defects:

- `git status`: Check the current status of your working directory and staging area.
- `git diff`: Show changes between commits, commit and working tree, etc.
- `git log`: Display commit history.
- `git merge <branch>`: Merge the specified branch into the current branch.
- `git rebase <branch>`: Reapply commits on top of another base tip.
- `git reset --hard <commit>`: Reset the current branch to a specific commit, discarding all changes.
- `git revert <commit>`: Create a new commit that undoes the changes of a previous commit.
- `git cherry-pick <commit>`: Apply the changes introduced by some existing commits.
- `git stash`: Temporarily store modified files to be restored later.
- `git reflog`: Show a log of all ref updates.
