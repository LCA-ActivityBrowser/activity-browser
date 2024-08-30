#! /bin/sh

# input variables:
# $1: commit message
# $2: GH token ${{ secrets.GITHUB_TOKEN }}

cd ..
git clone https://github.com/$GITHUB_REPOSITORY.wiki.git
yes | cp -rf activity-browser/docs/wiki/* activity-browser.wiki/
cd activity-browser.wiki
grep -lr "link:[a-zA-Z0-9_.-]*.asciidoc.*" .| xargs -r sed -i "s/.asciidoc//g"
if git diff-index --quiet HEAD && [ ! -n "$(git status -s)" ]; then
  echo "Wiki documentation was not changed, documentation, not updating."
  set +e
  pkill -9 -P $$ &> /dev/null || true
  exit 0
else
  echo "Wiki documentation was changed, documentation, updating."
  git config --global user.name "$GITHUB_ACTOR"
  git config --global user.email "$(git log -n 1 --pretty=format:%ae)"
  git status
  git add .
  git commit -m "$1"
  git remote add origin-wiki "https://$GITHUB_ACTOR:$2@github.com/$GITHUB_REPOSITORY.wiki"
  git push origin-wiki master
fi
cd "activity-browser"
