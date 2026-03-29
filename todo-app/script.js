class TodoApp {
    constructor() {
        this.todos = JSON.parse(localStorage.getItem('todoList')) || [];
        this.currentFilter = 'all';
        this.storageKey = 'todoList';

        // DOM Elements
        this.taskInput = document.getElementById('taskInput');
        this.addTaskBtn = document.getElementById('addTaskBtn');
        this.taskList = document.getElementById('taskList');
        this.taskCountSpan = document.getElementById('taskCount');
        this.clearCompletedBtn = document.getElementById('clearCompletedBtn');
        this.filterBtns = document.querySelectorAll('.filter-btn');

        this.init();
    }

    init() {
        // Event Listeners
        this.addTaskBtn.addEventListener('click', () => this.addTodo());
        this.taskInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') this.addTodo();
        });

        this.clearCompletedBtn.addEventListener('click', () => this.clearCompleted());

        this.filterBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                this.currentFilter = e.target.dataset.filter;
                this.updateFilterButtons(e.target);
                this.render();
            });
        });

        this.render();
    }

    addTodo() {
        const text = this.taskInput.value.trim();
        if (text === '') return;

        // XSS Protection / HTML Escaping
        const escapedText = this.escapeHTML(text);

        const newTodo = {
            id: Date.now(),
            text: escapedText,
            completed: false
        };

        this.todos.push(newTodo);
        this.saveAndRender();
        this.taskInput.value = '';
        this.taskInput.focus();
    }

    toggleTodo(id) {
        this.todos = this.todos.map(todo => 
            todo.id === id ? { ...todo, completed: !todo.completed } : todo
        );
        this.saveAndRender();
    }

    deleteTodo(id) {
        this.todos = this.todos.filter(todo => todo.id !== id);
        this.saveAndRender();
    }

    clearCompleted() {
        this.todos = this.todos.filter(todo => !todo.completed);
        this.saveAndRender();
    }

    updateFilterButtons(activeBtn) {
        this.filterBtns.forEach(btn => btn.classList.remove('active'));
        activeBtn.classList.add('active');
    }

    saveAndRender() {
        localStorage.setItem(this.storageKey, JSON.stringify(this.todos));
        this.render();
    }

    escapeHTML(str) {
        const div = document.createElement('div');
        div.textContent = str;
        return div.innerHTML;
    }

    render() {
        let filteredTodos = this.todos;
        if (this.currentFilter === 'active') {
            filteredTodos = this.todos.filter(t => !t.completed);
        } else if (this.currentFilter === 'completed') {
            filteredTodos = this.todos.filter(t => t.completed);
        }

        this.taskList.innerHTML = '';
        filteredTodos.forEach(todo => {
            const li = document.createElement('li');
            li.className = `todo-item ${todo.completed ? 'completed' : ''}`;
            li.innerHTML = `
                <div class="todo-item-content">
                    <input type="checkbox" ${todo.completed ? 'checked' : ''}>
                    <span>${todo.text}</span>
                </div>
                <button class="delete-btn" title="Delete Task">&times;</button>
            `;

            // Event Listeners for the new elements
            li.querySelector('input').addEventListener('change', () => this.toggleTodo(todo.id));
            li.querySelector('.delete-btn').addEventListener('click', () => this.deleteTodo(todo.id));

            this.taskList.appendChild(li);
        });

        const activeCount = this.todos.filter(t => !t.completed).length;
        this.taskCountSpan.textContent = `${activeCount} task${activeCount !== 1 ? 's' : '' } left`;
    }
}

// Initialize the app when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TodoApp();
});
