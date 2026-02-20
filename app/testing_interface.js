/**
 * RAO-AGI Testing Interface Logic
 * 
 * Provides interactive board visualization and task verification for the benchmark.
 */

var currentTask = null;

/**
 * Attaches an event listener to the file input to load task definitions from JSON files.
 */
document.getElementById("file-input").addEventListener("change", function(e) {
  var file = e.target.files[0];
  if (!file) return;

  var reader = new FileReader();
  reader.onload = function(ev) {
    var task;
    try {
      task = JSON.parse(ev.target.result);
    } catch (err) {
      alert("Error: Unable to parse task JSON definition.");
      return;
    }
    loadTask(task);
  };
  reader.readAsText(file);
});

/**
 * Initializes the task visualization for a given task definition.
 * 
 * @param {Object} task - The task object containing ID, board state, and solutions.
 */
function loadTask(task) {
  currentTask = task;

  document.getElementById("task-id").textContent = task.id;
  document.getElementById("task-info").classList.remove("hidden");

  renderBoard(task.board);
  renderColumnButtons(task.columns);

  document.getElementById("board-area").classList.remove("hidden");
  document.getElementById("result").classList.add("hidden");
  document.getElementById("result").className = "hidden";

  var solutionArea = document.getElementById("solution-area");
  if (task.solution !== undefined) {
    document.getElementById("solution-value").textContent = "column " + task.solution;
    solutionArea.classList.remove("hidden");
  } else {
    solutionArea.classList.add("hidden");
  }
}

/**
 * Dynamically renders the Connect Four board state.
 * 
 * @param {Array<string>} rows - Array of strings representing the board state.
 */
function renderBoard(rows) {
  var board = document.getElementById("board");
  board.innerHTML = "";
  for (var r = 0; r < rows.length; r++) {
    var rowEl = document.createElement("div");
    rowEl.className = "row";
    for (var c = 0; c < rows[r].length; c++) {
      var cell = document.createElement("div");
      var ch = rows[r][c];
      cell.className = "cell" + (ch !== "." ? " " + ch : "");
      cell.textContent = ch === "." ? "" : ch;
      rowEl.appendChild(cell);
    }
    board.appendChild(rowEl);
  }
}

/**
 * Renders column selection buttons for move testing.
 * 
 * @param {Array<string>} columns - List of column labels for the task.
 */
function renderColumnButtons(columns) {
  var container = document.getElementById("column-buttons");
  container.innerHTML = "";
  for (var i = 0; i < columns.length; i++) {
    (function(col) {
      var btn = document.createElement("button");
      btn.textContent = col;
      btn.addEventListener("click", function() {
        processPlayerMove(col);
      });
      container.appendChild(btn);
    })(columns[i]);
  }
}

/**
 * Processes a move selection and validates its legality.
 * 
 * @param {string} col - The column label selected by the user.
 */
function processPlayerMove(col) {
  if (!currentTask) return;

  var colIndex = parseInt(col, 10);
  var board = currentTask.board;

  // Validate column range
  if (colIndex < 0 || colIndex >= board[0].length) {
    displayFeedback("Selection error: Column index out of range.", false);
    return;
  }

  // Verify column capacity (row 0 is the top of the board)
  if (board[0][colIndex] !== ".") {
    displayFeedback("Invalid selection: Column " + col + " is full.", false);
    return;
  }

  displayFeedback("Selected column: " + col, true);
}

/**
 * Updates the user interface with feedback regarding a move selection.
 * 
 * @param {string} msg - Message to display.
 * @param {boolean} isLegal - Indicates if the move is legal.
 */
function displayFeedback(msg, isLegal) {
  var el = document.getElementById("result");
  el.textContent = msg;
  el.className = isLegal ? "legal" : "illegal";
  el.classList.remove("hidden");
}
