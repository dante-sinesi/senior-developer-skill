"""Corpus etiquetado para medir las heurísticas de `documentar-proyecto` (reglas de negocio candidatas).

Cada entrada es (lenguaje, línea de código, tipo esperado o None). El tipo esperado es lo que una persona que conoce el negocio marcaría como regla:
un umbral, una validación, un permiso, una lista de estados o una constante de negocio. `None` es ruido que NO debe proponerse como regla: contadores de
bucles, códigos HTTP, tiempos de espera, paginación, índices, versiones, comprobaciones de «no vacío». Las líneas son de mentira pero con la forma
de código real; las del tipo `None` son las trampas que más se repiten en los proyectos.
"""

# --- Python
PY = [
    ("py", "if total > 10000:", "umbral"),
    ("py", "if edad < 18:", "umbral"),
    ("py", "elif saldo >= 5000 and score > 700:", "umbral"),
    ("py", "if pedido.descuento > 0.25:", "umbral"),
    ("py", "if dias_de_mora > 30:", "umbral"),
    ("py", "if stock < 5:", "umbral"),
    ("py", "RECARGO_POR_MORA = 15", "constante"),
    ("py", "IVA = 21", "constante"),
    ("py", "COMISION_MINIMA = 150", "constante"),
    ("py", "@login_required", "permiso"),
    ("py", "@permission_required('facturas.anular')", "permiso"),
    ("py", "if not user.is_admin:", "permiso"),
    ("py", "class EstadoPedido(Enum):", "estados"),
    ("py", "nombre = models.CharField(max_length=120)", "validación"),
    ("py", "validators=[MinValueValidator(1)]", "validación"),
    ("py", "for i in range(10):", None),
    ("py", "if i < 10:", None),
    ("py", "while intentos < 3:", None),
    ("py", "if len(items) > 0:", None),
    ("py", "if len(nombre) == 0:", None),
    ("py", "if respuesta.status_code == 200:", None),
    ("py", "if resp.status == 404:", None),
    ("py", "timeout = 30", None),
    ("py", "TIMEOUT_SEGUNDOS = 30", None),
    ("py", "PAGE_SIZE = 20", None),
    ("py", "if pagina > 1:", None),
    ("py", "MAX_REINTENTOS = 5", None),
    ("py", "if x == 0:", None),
    ("py", "if resultado is None or resultado == -1:", None),
    ("py", "if version >= 3:", None),
    ("py", "PUERTO = 8080", None),
    ("py", "SECRET_LENGTH = 32", None),
    ("py", "y = x * 2", None),
]

# --- PHP
PHP = [
    ("php", "if ($total > 10000) {", "umbral"),
    ("php", "if ($cliente->edad < 18) {", "umbral"),
    ("php", "if ($saldo <= 0 && $limite > 1500) {", "umbral"),
    ("php", "define('IVA', 21);", "constante"),
    ("php", "const RECARGO_MORA = 15;", "constante"),
    ("php", "'email' => 'required|email|max:255',", "validación"),
    ("php", "'precio' => 'required|numeric|min:0',", "validación"),
    ("php", "if ($user->hasRole('admin')) {", "permiso"),
    ("php", "$this->authorize('anular', $factura);", "permiso"),
    ("php", "const ESTADO_PAGADO = 2;", "estados"),
    ("php", "for ($i = 0; $i < 10; $i++) {", None),
    ("php", "if ($i == 0) {", None),
    ("php", "if ($response->getStatusCode() === 200) {", None),
    ("php", "if (count($items) > 0) {", None),
    ("php", "$perPage = 15;", None),
    ("php", "set_time_limit(300);", None),
    ("php", "if ($page > 1) {", None),
    ("php", "if (strlen($nombre) == 0) {", None),
    ("php", "$maxIntentos = 3;", None),
    ("php", "if (PHP_VERSION_ID >= 80000) {", None),
]

# --- JavaScript
JS = [
    ("js", "if (total > 10000) {", "umbral"),
    ("js", "if (user.age < 18) {", "umbral"),
    ("js", "if (saldo >= 5000 && score > 700) {", "umbral"),
    ("js", "const IVA = 21;", "constante"),
    ("js", "const COMISION_MINIMA = 150;", "constante"),
    ("js", "nombre: z.string().min(3).max(50),", "validación"),
    ("js", "email: Joi.string().email().required(),", "validación"),
    ("js", "if (user.hasPermission('facturas.anular')) {", "permiso"),
    ("js", "const ESTADO_PEDIDO = { PENDIENTE: 1, PAGADO: 2 };", "estados"),
    ("js", "for (let i = 0; i < 10; i++) {", None),
    ("js", "if (res.status === 200) {", None),
    ("js", "if (res.status === 404) {", None),
    ("js", "if (items.length > 0) {", None),
    ("js", "const TIMEOUT_MS = 5000;", None),
    ("js", "const PAGE_SIZE = 25;", None),
    ("js", "if (retries < 3) {", None),
    ("js", "const x = y * 2;", None),
    ("js", "if (index === 0) {", None),
    ("js", "const PORT = 3000;", None),
    ("js", "if (width > 768) {", None),
]

CORPUS = PY + PHP + JS
