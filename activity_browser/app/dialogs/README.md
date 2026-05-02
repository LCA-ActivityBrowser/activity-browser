# dialogs

Dialog windows for user interactions throughout Activity Browser.

## Overview

This directory contains modal and non-modal dialog windows used for various user interactions such as data entry, configuration, selection, and information display. Dialogs in the app directory are there because they are tightly integrated with Brightway2 or depend on the application for other reasons.

- Generally, action specific dialogs are located alongside the corresponding action in the `actions/` directory.
- Dialogs than can be applied more widely and are not intimately tied with either actions or Brightway2 are located in the `ui/dialogs/` directory.
- Only if the above two locations are not appropriate should a dialog be placed here.

What qualifies to be put in this directory is somewhat subjective, but the guiding principle is that these dialogs are core to the functioning of Activity Browser and are not easily reusable outside of it.