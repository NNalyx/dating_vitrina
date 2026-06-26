# Profile / Settings split

## Goal
Stop duplicating profile fields in Settings. Profile becomes the visual editor for the user's card; Settings holds feed/technical options.

## Profile changes
- Keep the existing profile card UI.
- Replace `prompt()` editors with full-screen editors styled like registration steps.
- Tapping a field opens an editor screen for that field:
  - `name`, `age`, `city` — single input + save button.
  - `gender`, `looking_for`, `goal` — option buttons grid.
  - `interests` — `interestPicker` screen.
  - `photo_file_id` — photo upload screen.
- Saving calls `PUT /api/me` and returns to the profile card.

## Settings changes
- Remove the "Моя анкета" block entirely.
- Keep feed filters and notifications toggles.
- Add a "Сбросить все просмотренные анкеты" button.
- New API: `POST /api/reset-views` clears the current user's `views` rows.

## Backend changes
- `database.py`: add `clear_views(viewer_id)` deleting `views` rows for the viewer.
- `web_routes.py`: add protected `POST /api/reset-views` endpoint.
- `docs/js/api.js`: add `resetViews()` method.
