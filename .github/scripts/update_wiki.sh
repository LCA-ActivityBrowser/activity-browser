#! /bin/sh

# input variables:
# $1: commit message
# $2: GH token ${{ secrets.GITHUB_TOKEN }}

# clone the current wiki git
cd ..
git clone https://github.com/$GITHUB_REPOSITORY.wiki.git
# extract the .git folder and empty the wiki folder
mkdir temp
yes | cp -rf activity-browser.wiki/.git temp
find activity-browser.wiki -mindepth 1 -delete
# copy the (potentially new) content from the main repo and the wiki .git folder to wiki folder and delete temp folder
yes | cp -rf activity-browser/docs/wiki/* activity-browser.wiki/
yes | cp -rf temp/.git activity-browser.wiki/
rm -rf temp
cd activity-browser.wiki
# check if changes were made
grep -lr "link:[a-zA-Z0-9_.-]*.asciidoc.*" .| xargs -r sed -i "s/.asciidoc//g"
if git diff-index --quiet HEAD && [ ! -n "$(git status -s)" ]; then
  # no changes
  echo "Wiki documentation was not changed, documentation, not updating."
  # return folders to original state
  cd ..
  rm -rf activity-browser.wiki
  cd activity-browser
  # exit script
  set +e
  pkill -9 -P $$ &> /dev/null || true
  exit 0
else
  # changes
  echo "Wiki documentation was changed, documentation, updating."
  # set github user
  git config --global user.name "$GITHUB_ACTOR"
  git config --global user.email "$(git log -n 1 --pretty=format:%ae)"
  # commit changes to wiki git
  git status
  git add .
  git commit -m "$1"
  # create origin and push
  git remote add origin-wiki "https://$GITHUB_ACTOR:$2@github.com/$GITHUB_REPOSITORY.wiki"
  git push origin-wiki master
  # return folders to original state
  cd ..
  rm -rf activity-browser.wiki
  cd activity-browser
fi
