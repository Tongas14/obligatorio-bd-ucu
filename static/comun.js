// Funciones compartidas por las pantallas de partidos, planillas y sanciones

async function api(metodo, url, cuerpo) {
  const opciones = { method: metodo, headers: {} };
  if (cuerpo !== undefined) {
    opciones.headers["Content-Type"] = "application/json";
    opciones.body = JSON.stringify(cuerpo);
  }
  const respuesta = await fetch(url, opciones);
  if (respuesta.status === 401) {
    location.href = "/login";
    throw new Error("Debe iniciar sesión");
  }
  const datos = await respuesta.json();
  if (respuesta.status === 403) throw new Error(datos.detail || "No tiene permisos");
  if (respuesta.status === 422) throw new Error("Hay datos inválidos en el formulario");
  if (datos && datos.error) throw new Error(datos.error);
  return datos;
}

function mostrarMensaje(texto, esError) {
  const caja = document.getElementById("mensaje");
  caja.textContent = texto;
  caja.className = "mensaje " + (esError ? "error" : "ok");
  caja.scrollIntoView({ block: "nearest" });
}

// Ejecuta una acción contra la API mostrando su resultado o su error
async function ejecutar(accion) {
  try {
    const datos = await accion();
    if (datos && datos.mensaje) mostrarMensaje(datos.mensaje, false);
    return datos;
  } catch (e) {
    mostrarMensaje(e.message, true);
    return null;
  }
}

function escapar(texto) {
  const div = document.createElement("div");
  div.textContent = texto == null ? "" : String(texto);
  return div.innerHTML;
}

function opcion(valor, texto, seleccionado) {
  return `<option value="${escapar(valor)}"${seleccionado ? " selected" : ""}>${escapar(texto)}</option>`;
}

async function cerrarSesion() {
  await fetch("/logout", { method: "POST" });
  location.href = "/login";
}
