# Zotero Connector implementation notes

The installed Zotero 10.0 application exposes a local Connector server at
`http://127.0.0.1:23119`. The implementation was checked against the installed
`app/omni.ja` source, especially:

- `chrome/content/zotero/xpcom/server/server_connector.js`
- `chrome/content/zotero/xpcom/server/saveSession.js`

The relevant write flow is:

1. `POST /connector/saveStandaloneAttachment?sessionID=<id>` with a PDF byte
   stream and an `X-Metadata` JSON header containing `sessionID`, `title`, and
   a local `file://` URL. Zotero stores the attachment in the selected target.
2. Zotero starts its own `RecognizeDocument.autoRecognizeItems()` flow when the
   file is recognizable.
3. `POST /connector/getRecognizedItem` with the same session ID waits for the
   recognizer and reports whether a recognized parent item is available.
4. `POST /connector/updateSession` with `target` and `tags` applies the target
   collection and the timestamp batch tag. The session code updates a child
   attachment's parent item when recognition has turned the attachment into a
   child item.

The Connector API derives the initial save target from the active Zotero pane.
The helper therefore reads `/connector/getSelectedCollection` before writing.
An explicit existing target ID can be applied through `updateSession`, but the
Connector API does not provide a collection-creation route. Batch identity is
therefore represented by a tag such as `batch:202608201946`; users can also
select an existing collection before the run.

Do not write Zotero's SQLite database directly. The local `/api/` Web API is
read-only for this purpose; Connector writes are the supported desktop route.
