<?php
defined('BASEPATH') OR exit('No direct script access allowed');

if (!function_exists('enviar_whatsapp')) {
    /**
     * Enviar mensaje de WhatsApp a través del Socket Server
     *
     * @param string $ruc RUC del emisor (Cliente autenticado)
     * @param string $celular Número de destino (519...)
     * @param string $mensaje Texto del mensaje
     * @param string $imagen (Opcional) URL o Path de imagen
     * @return bool|array Respuesta del servidor
     */
    function enviar_whatsapp($ruc, $celular, $mensaje, $imagen = null) {
        // URL de tu servidor Node.js (Asegúrate que el puerto coincida, por defecto es 3000 o 8000)
        // Si está en el mismo servidor: http://localhost:3000/api/venta
        // Si es remoto: http://jsjperu.net:3000/api/venta
        $url = 'http://localhost:3000/api/venta'; 

        $data = array(
            'ruc' => $ruc,
            'phone_number' => $celular,
            'message' => $mensaje
        );

        if ($imagen) {
            $data['image_path'] = $imagen;
        }

        // Inicializar cURL
        $ch = curl_init($url);
        
        // Configurar opciones
        curl_setopt($ch, CURLOPT_RETURNTRANSFER, true);
        curl_setopt($ch, CURLOPT_POST, true);
        curl_setopt($ch, CURLOPT_POSTFIELDS, json_encode($data));
        curl_setopt($ch, CURLOPT_HTTPHEADER, array(
            'Content-Type: application/json',
            'Content-Length: ' . strlen(json_encode($data))
        ));
        curl_setopt($ch, CURLOPT_TIMEOUT, 5); // Timeout de 5 segundos para no colgar PHP

        // Ejecutar
        $result = curl_exec($ch);
        $http_code = curl_getinfo($ch, CURLINFO_HTTP_CODE);
        
        if (curl_errno($ch)) {
            log_message('error', 'Error WhatsApp Curl: ' . curl_error($ch));
            curl_close($ch);
            return false;
        }
        
        curl_close($ch);

        return ($http_code == 200) ? json_decode($result, true) : false;
    }
}
