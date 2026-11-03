# Document review

Improve `index.html` so a reviewer can read a revision and approve it or request changes. Keep the fixture standalone with no dependencies. Preserve the document title, author, revision identity, content, decision status, and consequences of approving a specific revision. Editing the content must create a new unapproved revision; an earlier approval must never silently approve the edited content.

Remove information that does not help this task. Do not add navigation, analytics, authentication, or a backend. Check desktop and narrow layouts, keyboard controls, and the edit-after-approval path in a browser if available. If unavailable, clearly state that runtime UX remains unverified. You may serve this directory locally for testing.

Changing between read and edit modes should preserve the user's place and keep unrelated decision controls stable. Choose an editing pattern appropriate to this small task; don't introduce a modal just to conceal layout movement. Error and cancel states must preserve input or saved content as appropriate, and long content must remain accessible.
