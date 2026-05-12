const express = require('express');
const authController = require('../controllers/auth.controller');
const validateRequest = require('../middleware/validation.middleware');
const { authSchemas } = require('../schemas/auth.schemas');
const { authLimiter } = require('../middleware/rate-limit.middleware');

const router = express.Router();

/**
 * @openapi
 * /auth/login:
 *   post:
 *     summary: Login
 *     tags: [Auth]
 *     requestBody:
 *       required: true
 *       content:
 *         application/json:
 *           schema:
 *             type: object
 *             required: [email, password]
 *             properties:
 *               email: { type: string, format: email }
 *               password: { type: string }
 *     responses:
 *       200:
 *         description: OK
 */
router.post('/login', authLimiter, validateRequest(authSchemas.login), authController.login);

/**
 * @openapi
 * /auth/register:
 *   post:
 *     summary: Register
 *     tags: [Auth]
 */
router.post('/register', authLimiter, validateRequest(authSchemas.register), authController.register);
router.post('/refresh', validateRequest(authSchemas.refresh), authController.refreshToken);
router.post('/logout', authController.logout);
router.post('/forgot-password', authLimiter, validateRequest(authSchemas.forgotPassword), authController.forgotPassword);
router.post('/reset-password', authLimiter, validateRequest(authSchemas.resetPassword), authController.resetPassword);

module.exports = router;
