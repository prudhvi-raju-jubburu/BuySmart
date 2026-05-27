import React from 'react';
import './Modal.css';

const Modal = ({ isOpen, onClose, children, title }) => {
    if (!isOpen) return null;

    return (
        <div className="modal-backdrop" onClick={onClose}>
            <div className="modal-content" onClick={e => e.stopPropagation()}>
                <button className="modal-close" onClick={onClose}>&times;</button>
                {title && <h2>{title}</h2>}
                {children}
            </div>
        </div>
    );
};

export default Modal;
